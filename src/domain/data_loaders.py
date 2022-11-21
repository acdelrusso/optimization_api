from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from .models import Asset
from fastapi import HTTPException, status
from .approvals import ApprovalSchema, VpackApprovals, VFNApprovals
from .priorities import PriorityProvider, GeneralPriorities, VariableCosts
from .relational_data import RunRates


def validate_table_in_data(tablename: str, data: dict):
    if data.get(tablename) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No table named {tablename} in input file. Input file must have properly formatted {tablename} tab.",
        )


class DataFormatter(ABC):
    @abstractmethod
    def load():
        pass


class LROPloader(DataFormatter):
    @staticmethod
    def load(demand_scenario: str, data: dict[pd.DataFrame]) -> tuple[dict, list[int]]:
        validate_table_in_data("LROP", data)
        lrop = data["LROP"].fillna("")
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
        years = sorted(lrop["Year"].unique())
        lrop = lrop.to_dict()
        return lrop, years


class AssetLoader(DataFormatter):
    @staticmethod
    def load(data: dict[pd.DataFrame]) -> set[Asset]:
        validate_table_in_data("Capacities", data)
        capacities = (
            data["Capacities"]
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
        if data.get("Commitments", None) is not None:
            commitments = data["Commitments"].set_index("Site").to_dict("index")
        return {Asset.from_record(record, commitments) for record in capacities}


class ApprovalsLoader(DataFormatter):
    def load(
        self, data: dict[pd.DataFrame], strategy: str, years: list[int]
    ) -> ApprovalSchema:
        validate_table_in_data("Approvals", data)
        approvals = data["Approvals"]
        if strategy == "vpack":
            approvals = self._preformat_data(approvals, years)
            return VpackApprovals(
                {
                    (t.Asset, t.Region, t.Image, t.Config, t.Product): (
                        t.Date_Start,
                        t.Date_Stop,
                    )
                    for t in approvals.itertuples(index=False)
                }
            )
        elif strategy == "vfn":
            return VFNApprovals(
                {
                    (t.Site, t.Region, t.Image, t.Product, t.Market): (
                        t.Date_Start,
                        t.Date_Stop,
                    )
                    for t in approvals.astype(
                        {"Date_Start": "datetime64[ns]", "Date_Stop": "datetime64[ns]"}
                    ).itertuples(index=False)
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Incompatable strategy {strategy} recieved in request. Approvals could not be generated.",
            )

    @staticmethod
    def _preformat_data(data: pd.DataFrame, years: list[int]) -> pd.DataFrame:
        df = pd.melt(
            data,
            id_vars=["Asset", "Region", "Image", "Config", "Product"],
            value_vars=years,
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

        return completed_approvals


class RunRatesLoader(DataFormatter):
    @staticmethod
    def load(data: dict[pd.DataFrame]) -> RunRates:
        validate_table_in_data("Run Rates", data)
        return RunRates(
            {
                (t.Asset, t.Image, t.Config): (t.Run_Rate, t.Avg_CO_hours)
                for t in data["Run Rates"].fillna("").itertuples(index=False)
            }
        )


class PrioritiesLoader(DataFormatter):
    def load(
        self, data: dict[pd.DataFrame], strategy: str, prioritization_schema, years
    ) -> PriorityProvider:
        prioritization_schema = self._get_prioritization_schema(
            prioritization_schema, data
        )
        approvals = ApprovalsLoader().load(data, strategy, years)

        return PriorityProvider(prioritization_schema, approvals)

    def _get_prioritization_schema(self, prioritization_schema: str, data):
        if prioritization_schema == "General Priorities":
            validate_table_in_data("General Priorities", data)
            general_priorities = data["General Priorities"]
            prioritization_schema = GeneralPriorities({})
            prioritization_schema.update(self._load_site_priorities(general_priorities))
            prioritization_schema.update(
                self._load_region_priorities(general_priorities)
            )
            prioritization_schema.update(
                self._load_product_priorities(general_priorities)
            )
            return prioritization_schema
        elif prioritization_schema == "Variable Costs":
            validate_table_in_data("Variable Costs", data)
            variable_costs = data["Variable Costs"]
            prioritization_schema = VariableCosts({})
            prioritization_schema.update(self._load_variable_costs(variable_costs))
            return prioritization_schema
        else:
            raise TypeError(
                f"Invalid Prioritization Schema Defined: {self.prioritization_schema}"
            )

    @staticmethod
    def _load_site_priorities(data) -> dict:
        site_priorities = data[["Asset", "Asset_Priority"]].fillna("")
        site_priorities = site_priorities[site_priorities.isna() == False]
        return {
            t.Asset: t.Asset_Priority for t in site_priorities.itertuples(index=False)
        }

    @staticmethod
    def _load_region_priorities(data) -> dict:
        region_priorities = data[["Asset_Region", "Region", "Region_Priority"]].fillna(
            ""
        )
        region_priorities = region_priorities[region_priorities.isna() == False]
        return {
            (t.Asset_Region, t.Region): t.Region_Priority
            for t in region_priorities.itertuples(index=False)
        }

    @staticmethod
    def _load_product_priorities(data) -> dict:
        product_priorities = data[
            ["Asset_Product", "Product", "Product_Priority"]
        ].fillna("")
        product_priorities = product_priorities[product_priorities.isna() == False]
        return {
            (t.Asset_Product, t.Product): t.Product_Priority
            for t in product_priorities.itertuples(index=False)
        }
