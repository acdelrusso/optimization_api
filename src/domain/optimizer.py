from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
import dataclasses
from .approvals import VpackApprovals, VFNApprovals, ApprovalSchema
from .priorities import GeneralPriorities, VariableCosts, PriorityProvider
from .relational_data import RunRates
from .models import Demand, Sku, Asset
import pyomo.environ as pe
from pyomo.opt import SolverFactory
import datetime as dt
from typing import Optional
from fastapi import HTTPException, status


class Optimizer:
    def __init__(
        self,
        assets: set[Asset],
        demand: Demand,
        priorities: PriorityProvider,
        run_rates: RunRates,
        years: list[int],
        applying_take_or_pay: bool = False,
        optimize_by_month: bool = False,
    ) -> None:
        self.assets = assets
        self.demand = demand
        self.priorities = priorities
        self.run_rates = run_rates
        self.years = years
        self.allocated_skus = set()
        self.applying_take_or_pay = applying_take_or_pay
        self.optimize_by_month = optimize_by_month

    def optimize_period(self, year: int, month: Optional[int] = None):
        print(year, month)
        model = pe.ConcreteModel()
        skus = set(self.demand.demand_for_date(year, month))
        SCALE = 12 if month is not None else 1
        optimization_date = (
            dt.datetime(year, month, 1) if month else dt.datetime(year, 1, 1)
        )
        assets = {
            asset for asset in self.assets if asset.launch_date <= optimization_date
        }
        model.q_sku_asset = pe.Var(skus, assets, bounds=(0, 1))

        def siting_constraint(model, sku, asset):
            return (
                model.q_sku_asset[sku, asset] * self.priorities.get_priority(sku, asset)
                >= 0
            )

        model.siting_constraint = pe.Constraint(skus, assets, rule=siting_constraint)

        def sku_constraint(model, sku):
            return sum(model.q_sku_asset[sku, asset] for asset in assets) <= 1

        model.sku_constraint = pe.Constraint(skus, rule=sku_constraint)

        if self.applying_take_or_pay:

            def asset_min_capacity_constraint(model, asset: Asset):
                if asset.min_capacities[year] == 0:
                    return pe.Constraint.Skip
                return (
                    sum(model.q_sku_asset[sku, asset] * sku.doses for sku in skus)
                    >= asset.min_capacities[year]
                )

            model.site_min_constraint = pe.Constraint(
                assets, rule=asset_min_capacity_constraint
            )

        def site_max_capacity_constraint(model, asset: Asset):
            return (
                sum(
                    model.q_sku_asset[sku, asset]
                    * self.run_rates.get_utilization(sku, asset)
                    for sku in skus
                )
                <= 1
            )

        model.asset_max_capacity_constraint = pe.Constraint(
            assets, rule=site_max_capacity_constraint
        )

        def objective_function(model):
            return sum(
                sum(
                    model.q_sku_asset[sku, asset]
                    * self.priorities.get_priority(sku, asset)
                    for asset in assets
                )
                for sku in skus
            )

        model.value = pe.Objective(rule=objective_function, sense=pe.maximize)

        opt = SolverFactory("glpk")
        opt.solve(model)

        self.solved_model = model

        return self._extract_solution_from(model, skus, assets)

    def _extract_solution_from(
        self, solved_model: pe.ConcreteModel, skus: set[Sku], assets: set[Asset]
    ):
        unmet_demand = Asset(
            "Unmet Demand", "UNMT", "ZUNMET", "N/A", "N/A", dt.datetime(2022, 1, 1), {}
        )

        allocated_skus = set()
        for sku in skus:
            unallocated = 1
            for asset in assets:
                if solved_model.q_sku_asset[sku, asset].value is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Model did not Converge for {sku.date.year, sku.date.month}. Check your input file and take or pays.",
                    )
                if (
                    sku.product == "Gardasil 9"
                    and asset.name == "Coral"
                    and solved_model.q_sku_asset[sku, asset].value > 0
                ):
                    print(
                        asset.name,
                        sku.product,
                        self.priorities.get_priority(sku, asset),
                        solved_model.q_sku_asset[sku, asset].value,
                    )
                if solved_model.q_sku_asset[sku, asset].value > 0.001:
                    allocated_skus.add(
                        dataclasses.replace(
                            sku,
                            doses=round(
                                sku.doses * solved_model.q_sku_asset[sku, asset].value
                            ),
                            allocated_to=asset,
                            percent_utilization=self.run_rates.get_utilization(
                                sku,
                                asset,
                                solved_model.q_sku_asset[sku, asset].value,
                            ),
                        )
                    )
                    unallocated -= solved_model.q_sku_asset[sku, asset].value
            if unallocated > 0:
                allocated_skus.add(
                    dataclasses.replace(
                        sku,
                        doses=round(sku.doses * unallocated),
                        allocated_to=unmet_demand,
                        percent_utilization=0,
                    )
                )

        return allocated_skus


class AbstractOptimizerBuilder(ABC):
    def __init__(self, demand_scenario: str, prioritization_schema: str, file) -> None:
        pass

    @abstractmethod
    def _load_assets(self):
        pass

    @abstractmethod
    def _load_demand(self, demand_scenario: str):
        pass

    @abstractmethod
    def _load_priorities():
        pass

    @abstractmethod
    def _load_run_rates():
        pass


class OptimizerBuilder(AbstractOptimizerBuilder):
    def __init__(self, demand_scenario: str, prioritization_schema: str, file) -> None:
        self._data = pd.read_excel(file, sheet_name=None)
        self.demand_scenario = demand_scenario
        self.prioritization_schema = prioritization_schema

    def _load_demand(
        self, demand_scenario: str, monthly_offset: int = 0, monthize_capacity=False
    ) -> Demand:
        """Loads and formats the demand from the LROP tab of the inputs file

        Args:
            demand_scenario (str): the selected demand scenario to analyze (B, U or D) in the input file LROP tab

        Returns:
            Demand: Demand object which provides Sku objects for a given year and month.
        """
        lrop = self._data["LROP"].fillna("")
        lrop = lrop[lrop["Demand Scenario"] == demand_scenario].drop(
            "Demand Scenario", axis=1
        )
        lrop = (
            lrop.groupby(
                [
                    "Year",
                    "Material_Number",
                    "Image",
                    "Config",
                    "Region",
                    "Market",
                    "Country_ID",
                    "Product",
                    "Product_ID",
                ]
            )
            .sum()
            .reset_index()
        )
        self.years = sorted(lrop["Year"].unique())
        lrop = lrop.to_dict()
        return Demand(lrop, monthly_offset, monthize_capacity)

    def _load_assets(self) -> set[Asset]:
        """Loads all assets

        Returns:
            set[Asset]: _description_
        """
        capacities = (
            self._data["Capacities"]
            .fillna("")
            .astype(
                {
                    2022: float,
                    2023: float,
                    2024: float,
                    2025: float,
                    2026: float,
                    2027: float,
                    2028: float,
                    2029: float,
                    2030: float,
                    2031: float,
                }
            )
            .to_dict("records")
        )
        commitments = None
        if self._data.get("Commitments", None) is not None:
            commitments = self._data["Commitments"].set_index("Site").to_dict("index")
        return {Asset.from_record(record, commitments) for record in capacities}

    def _load_approvals(self, strategy: str) -> ApprovalSchema:
        # TODO: Code Smell, need to clean this up somehow
        if strategy == "vpack":
            approvals = self._data["Approvals"]
            df = pd.melt(
                approvals,
                id_vars=["Asset", "Region", "Image", "Config", "Product"],
                value_vars=self.years,
                var_name="Year",
                value_name="Approval",
            )

            completed_approvals = (
                df[df["Approval"] != 0]
                .drop(columns={"Approval"})
                .groupby(["Asset", "Region", "Image", "Config", "Product"])
                .agg({"Year": [np.min, np.max]})
                .reset_index()
            )
            aggregate_columns = [
                "Date_Start",
                "Date_Stop",
            ]
            completed_approvals.columns = (
                list(completed_approvals.columns.droplevel(1)[:5]) + aggregate_columns
            )

            for col in aggregate_columns:
                completed_approvals[col] = pd.to_datetime(
                    completed_approvals[col], format="%Y"
                )

            return VpackApprovals(
                {
                    (t.Asset, t.Region, t.Image, t.Config, t.Product): (
                        t.Date_Start,
                        t.Date_Stop,
                    )
                    for t in completed_approvals.itertuples(index=False)
                }
            )
        return VFNApprovals(
            {
                (t.Site, t.Region, t.Image, t.Product, t.Market): (
                    t.Date_Start,
                    t.Date_Stop,
                )
                for t in self._data["Approvals"]
                .astype({"Date_Start": "datetime64[ns]", "Date_Stop": "datetime64[ns]"})
                .itertuples(index=False)
            }
        )

    def _get_prioritization_schema(self):
        if self.prioritization_schema == "General Priorities":
            prioritization_schema = GeneralPriorities({})
            prioritization_schema.update(self._load_site_priorities())
            prioritization_schema.update(self._load_region_priorities())
            prioritization_schema.update(self._load_product_priorities())
            return prioritization_schema
        elif self.prioritization_schema == "Variable Costs":
            prioritization_schema = VariableCosts({})
            prioritization_schema.update(self._load_variable_costs())
            return prioritization_schema
        else:
            raise TypeError(
                f"Invalid Prioritization Schema Defined: {self.prioritization_schema}"
            )

    def _load_priorities(self, strategy: str) -> PriorityProvider:
        prioritization_scheme = self._get_prioritization_schema()
        approvals = self._load_approvals(strategy)
        return PriorityProvider(prioritization_scheme, approvals)

    def _load_variable_costs(self):
        costs = self._data["Variable Costs"]
        return {
            (t.Site, t.Year, t.Product): t.Price for t in costs.itertuples(index=False)
        }

    def _load_site_priorities(self) -> dict:
        site_priorities = self._data["General Priorities"][
            ["Asset", "Asset_Priority"]
        ].fillna("")
        site_priorities = site_priorities[site_priorities.isna() == False]
        return {
            t.Asset: t.Asset_Priority for t in site_priorities.itertuples(index=False)
        }

    def _load_region_priorities(self) -> dict:
        region_priorities = self._data["General Priorities"][
            ["Asset_Region", "Region", "Region_Priority"]
        ].fillna("")
        region_priorities = region_priorities[region_priorities.isna() == False]
        return {
            (t.Asset_Region, t.Region): t.Region_Priority
            for t in region_priorities.itertuples(index=False)
        }

    def _load_product_priorities(self) -> dict:
        product_priorities = self._data["General Priorities"][
            ["Asset_Product", "Product", "Product_Priority"]
        ].fillna("")
        product_priorities = product_priorities[product_priorities.isna() == False]
        return {
            (t.Asset_Product, t.Product): t.Product_Priority
            for t in product_priorities.itertuples(index=False)
        }

    def _load_run_rates(self) -> RunRates:
        return RunRates(
            {
                (t.Asset, t.Image, t.Config): (t.Run_Rate, t.Avg_CO_hours)
                for t in self._data["Run Rates"].fillna("").itertuples(index=False)
            }
        )


class OptimizerDirector:
    def __init__(self, builder: OptimizerBuilder) -> None:
        self.builder = builder

    def build_optimizer(self, strategy):
        if strategy == "vpack":
            return Optimizer(
                self.builder._load_assets(),
                self.builder._load_demand(self.builder.demand_scenario),
                self.builder._load_priorities(strategy),
                self.builder._load_run_rates(),
                self.builder.years,
            )
        elif strategy == "vfn":
            return Optimizer(
                self.builder._load_assets(),
                self.builder._load_demand(
                    self.builder.demand_scenario,
                    monthly_offset=6,
                    monthize_capacity=True,
                ),
                self.builder._load_priorities(strategy),
                self.builder._load_run_rates(),
                self.builder.years[:-1],
                applying_take_or_pay=True,
                optimize_by_month=False,
            )
