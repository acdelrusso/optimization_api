from abc import ABC, abstractmethod
import os
import pandas as pd
import numpy as np
import dataclasses
from .approvals import VpackApprovals, VFNApprovals
from .priorities import GeneralPriorities, VariableCosts, PriorityProvider
from .relational_data import RunRates
from .models import Demand, Sku, Asset
import pyomo.environ as pe
from pyomo.opt import SolverFactory
import datetime as dt

my_path = os.path.abspath(os.path.dirname(__file__))
path_to_standard_input = os.path.join(my_path, "../inputs/master.xlsx")


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

    def optimize_period(self, year: int):
        model = pe.ConcreteModel()
        skus = set(self.demand.demand_for_date(year))
        model.q_sku_asset = pe.Var(skus, self.assets, bounds=(0, 1))

        def siting_constraing(model, sku, asset):
            if self.priorities.get_priority(sku, asset) < 0:
                return model.q_sku_asset[sku, asset] == 0
            return (
                model.q_sku_asset[sku, asset]
                * self.priorities.get_priority(sku, asset)
                * self.run_rates.get_utilization(sku, asset)
                >= 0
            )

        model.siting_constraints = pe.Constraint(
            skus, self.assets, rule=siting_constraing
        )

        def sku_constraint(model, sku):
            return sum(model.q_sku_asset[sku, asset] for asset in self.assets) <= 1

        model.sku_constraint = pe.Constraint(skus, rule=sku_constraint)

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
            self.assets, rule=site_max_capacity_constraint
        )

        def objective_function(model):
            return sum(
                sum(
                    model.q_sku_asset[sku, asset]
                    * self.priorities.get_priority(sku, asset)
                    for asset in self.assets
                )
                for sku in skus
            )

        model.value = pe.Objective(rule=objective_function, sense=pe.maximize)

        opt = SolverFactory("glpk")
        opt.solve(model)

        self.solved_model = model

        self.allocated_skus.update(self._extract_solution_from(model, skus))

    def optimize(self):
        for year in self.years:
            self.optimize_period(year)

    def _extract_solution_from(self, solved_model: pe.ConcreteModel, skus: set[Sku]):
        unmet_demand = Asset(
            "Unmet Demand", "UNMT", "ZUNMET", "N/A", "N/A", dt.datetime(2022, 1, 1), {}
        )

        allocated_skus = set()
        for sku in skus:
            unallocated = 1
            for asset in self.assets:
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
    def __init__(self, demand_scenario: str, file=None) -> None:
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
    def __init__(
        self, demand_scenario: str, prioritization_schema: str, file=None
    ) -> None:
        if file is None:
            file = path_to_standard_input
        self._data = pd.read_excel(file, sheet_name=None)
        self.demand_scenario = demand_scenario
        self.prioritization_schema = prioritization_schema

    def _load_demand(self, demand_scenario: str) -> Demand:
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
        self.years = sorted(lrop["Year"].unique())
        return Demand(lrop)

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
        if self._data.get("Commitments", None):
            commitments = self._data["Commitments"].set_index("Site").to_dict("index")
        return {Asset.from_record(record, commitments) for record in capacities}

    def _load_approvals(self, kind: str) -> VpackApprovals:
        if kind == "vpack":
            approvals = self._data["Approvals"].fillna("")
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

            completed_approvals.columns = list(
                completed_approvals.columns.droplevel(1)[:5]
            ) + [
                "Date_Start",
                "Date_Stop",
            ]

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
                (t.Site, t.Product, t.Image, t.Region, t.Market): (
                    t.Date_Start,
                    t.Date_Stop,
                )
                for t in self._data["Approvals"]
                .astype({"Date_Approval": "datetime64[ns]"})
                .itertuples(index=False)
            }
        )

    def _get_prioritization_schema(self):
        if self.prioritization_schema == "General Priorities":
            return GeneralPriorities({})
        elif self.prioritization_schema == "Variable Costs":
            return VariableCosts({})
        else:
            raise TypeError(
                f"Invalid Prioritization Schema Defined: {self.prioritization_schema}"
            )

    def _load_priorities(self, kind: str) -> GeneralPriorities:
        prioritization_scheme = self._get_prioritization_schema()
        approvals = self._load_approvals(kind)
        priorities = PriorityProvider(prioritization_scheme, approvals)
        priorities.update(self._load_site_priorities())
        priorities.update(self._load_region_priorities())
        priorities.update(self._load_product_priorities())

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

    def build_optimizer(self, kind):
        return Optimizer(
            self.builder._load_assets(),
            self.builder._load_demand(self.builder.demand_scenario),
            self.builder._load_priorities(kind),
            self.builder._load_run_rates(),
            self.builder.years,
        )

    def build_vfn_optimizer(self):
        pass
