import os
import pandas as pd
import numpy as np
import dataclasses
from .relational_data import Priorities, RunRates, Approvals
from .sku import Demand, Sku
from .asset import Asset
import pyomo.environ as pe
from pyomo.opt import SolverFactory

my_path = os.path.abspath(os.path.dirname(__file__))
path_to_standard_input = os.path.join(my_path, "../inputs/master.xlsx")


class Optimizer:
    def __init__(
        self,
        assets: set[Asset],
        demand: Demand,
        priorities: Priorities,
        run_rates: RunRates,
        years: list[int],
    ) -> None:
        self.assets = assets
        self.demand = demand
        self.priorities = priorities
        self.run_rates = run_rates
        self.years = years
        self.allocated_skus = set()

    def optimize_period(self, year: int):
        model = pe.ConcreteModel()
        skus = set(self.demand.demand_for_year(year))
        model.q_sku_asset = pe.Var(skus, self.assets, bounds=(0, 1))

        def siting_constraing(model, sku, asset):
            if (
                self.priorities.get_priority(sku, asset) < 0
                or self.run_rates.get_utilization(sku, asset) == 0
            ):
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
        unmet_demand = Asset("Unmet Demand", "UNMT", "ZUNMET", "N/A", "N/A", {})

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


class OptimizerBuilder:
    def __init__(self, demand_scenario: str, file=None) -> None:
        if file is None:
            file = path_to_standard_input
        self._data = pd.read_excel(file, sheet_name=None)
        self.demand_scenario = demand_scenario

    def _load_demand(self, demand_scenario: str) -> Demand:
        """Loads and formats the demand from the LROP tab of the inputs file

        Args:
            demand_scenario (str): the selected demand scenario to analyze (B, U or D) in the input file LROP tab

        Returns:
            Demand: Demand object which provides Sku objects for a given year and month.
        """
        lrop = self._data["LROP"]
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
        return {Asset.from_record(record) for record in capacities}

    def _load_approvals(self) -> Approvals:
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

        completed_approvals.columns = list(
            completed_approvals.columns.droplevel(1)[:5]
        ) + [
            "Year_Start",
            "Year_Stop",
        ]

        return Approvals(
            {
                (t.Asset, t.Region, t.Image, t.Config, t.Product): (
                    t.Year_Start,
                    t.Year_Stop,
                )
                for t in completed_approvals.itertuples(index=False)
            }
        )

    def _load_priorities(self) -> Priorities:
        priorities = Priorities({}, self._load_approvals())
        for image in ["VIAL", "SYRINGE"]:
            priorities.update(self._load_site_priorities(image))
            priorities.update(self._load_region_priorities(image))
            priorities.update(self._load_product_priorities(image))
        return priorities

    def _load_site_priorities(self, image) -> dict:
        site_priorities = self._data[f"{image} Priorities"][["Asset", "Asset_Priority"]]
        site_priorities = site_priorities[site_priorities.isna() == False]
        return {
            t.Asset: t.Asset_Priority for t in site_priorities.itertuples(index=False)
        }

    def _load_region_priorities(self, image) -> dict:
        region_priorities = self._data[f"{image} Priorities"][
            ["Asset_Region", "Region", "Region_Priority"]
        ]
        region_priorities = region_priorities[region_priorities.isna() == False]
        return {
            (t.Asset_Region, t.Region): t.Region_Priority
            for t in region_priorities.itertuples(index=False)
        }

    def _load_product_priorities(self, image) -> dict:
        product_priorities = self._data[f"{image} Priorities"][
            ["Asset_Product", "Product", "Product_Priority"]
        ]
        product_priorities = product_priorities[product_priorities.isna() == False]
        return {
            (t.Asset_Product, t.Product): t.Product_Priority
            for t in product_priorities.itertuples(index=False)
        }

    def _load_run_rates(self) -> RunRates:
        return RunRates(
            {
                (t.Asset, t.Image, t.Config): (t.Run_Rate, t.Avg_CO_hours)
                for t in self._data["Run Rates"].itertuples(index=False)
            }
        )

    def build_optimizer(self):
        return Optimizer(
            self._load_assets(),
            self._load_demand(self.demand_scenario),
            self._load_priorities(),
            self._load_run_rates(),
            self.years,
        )
