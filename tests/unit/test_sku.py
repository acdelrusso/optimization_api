from src.domain.models import Demand, Sku
import pytest
import pandas as pd


def test_sku_init(sku_values: dict):
    sku = Sku(**sku_values)

    for attr in sku_values:
        assert getattr(sku, attr) == sku_values[attr]


def test_sku_from_tuple(sku_values: dict):
    sku = Sku.from_tuple(
        (2022, "SYRINGE", "10x", "LA", "Peru", "PE", "Gardasil 9", "GSL", 50000, 10.0)
    )

    for attr in sku_values:
        assert getattr(sku, attr) == sku_values[attr]


def test_sku_to_tuple(sku_values):
    sku = Sku(**sku_values)

    assert sku.to_tuple() == (
        2022,
        "SYRINGE",
        "10x",
        "LA",
        "Peru",
        "PE",
        "Gardasil 9",
        "GSL",
        50000,
        10.0,
        None,
        None,
    )


def test_sku_to_dict(sku_values: dict):
    sku = Sku(**sku_values)

    assert sku.to_dict() == sku_values


@pytest.fixture
def lrop():
    return pd.DataFrame.from_dict(
        {
            "Year": [2022, 2022, 2023],
            "Image": ["SYRINGE", "SYRINGE", "SYRINGE"],
            "Config": ["1x", "10x", "1x"],
            "Region": ["LA", "US", "EEMEA"],
            "Market": ["Peru", "USA", "Syria"],
            "Country_ID": ["PE", "US", "SY"],
            "Product": ["Gardasil", "Gardail 9", "V181 Dengue"],
            "Product_ID": ["HPV", "GSL", "DEN"],
            "Total": [10000, 50000, 2000],
            "Batches": [2, 10, 1],
        }
    )


def test_demand_init(lrop: pd.DataFrame):

    demand = Demand(lrop)

    assert demand.data == {Sku.from_tuple(t) for t in lrop.itertuples(index=False)}


def test_demand_for_year(lrop: pd.DataFrame):
    year_to_check = 2022
    expected = {
        Sku.from_tuple(t) for t in lrop.itertuples(index=False) if t[0] == year_to_check
    }

    demand = Demand(lrop)

    assert set(demand.demand_for_date(year_to_check)) == expected
