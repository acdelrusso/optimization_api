import pandas as pd
import dataclasses
from .priorities import PriorityProvider
from .relational_data import RunRates
from .models import Demand, Sku, Asset
import pyomo.environ as pe
from pyomo.opt import SolverFactory
import datetime as dt
from typing import Optional
from fastapi import HTTPException, status
from .data_loaders import LROPloader, AssetLoader, PrioritiesLoader, RunRatesLoader


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
                        detail=f"""Model did not Converge for {sku.date.year, sku.date.month}.
                        Check your input file and take or pays.""",
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


class OptimizerBuilder:
    def __init__(self, demand_scenario: str, prioritization_schema: str, file) -> None:
        self._data = pd.read_excel(file, sheet_name=None)
        self.demand_scenario = demand_scenario
        self.prioritization_schema = prioritization_schema

    def build_optimizer(self, strategy: str):
        lrop, years = LROPloader().load(self.demand_scenario, self._data)
        assets = AssetLoader().load(self._data)
        priorities = PrioritiesLoader().load(
            self._data, strategy, self.prioritization_schema, years
        )
        run_rates = RunRatesLoader().load(self._data)

        if strategy == "vpack":
            return Optimizer(assets, Demand(lrop), priorities, run_rates, years)
        elif strategy == "vfn":
            return Optimizer(
                assets,
                Demand(lrop, months_to_offset=6, monthize_capacity=True),
                priorities,
                run_rates,
                years[-1],
                applying_take_or_pay=True,
            )
