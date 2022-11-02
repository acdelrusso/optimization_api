from src.domain.models import Demand, Sku
import pytest
import pandas as pd
import datetime as dt


def test_sku_init(sku_values: dict):
    sku = Sku(**sku_values)

    for attr in sku_values:
        assert getattr(sku, attr) == sku_values[attr]


def test_sku_from_tuple(sku_values: dict):
    sku = Sku.from_tuple(
        (
            dt.datetime(year=2022, month=1, day=1),
            "SYRINGE",
            "10x",
            "LA",
            "Peru",
            "PE",
            "Gardasil 9",
            "GSL",
            50000,
            10.0,
        )
    )

    for attr in sku_values:
        assert getattr(sku, attr) == sku_values[attr]


def test_sku_to_tuple(sku_values):
    sku = Sku(**sku_values)

    assert sku.to_tuple() == (
        dt.datetime(year=2022, month=1, day=1),
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
    expected = set()
    for t in lrop.itertuples(index=False):
        (year, *rest) = t
        expected.add(Sku.from_tuple((dt.datetime(year=year, month=1, day=1), *rest)))

    assert demand.data == expected


def test_demand_for_year(lrop: pd.DataFrame):
    year_to_check = 2022
    demand = Demand(lrop)
    expected = set()
    for t in lrop.itertuples(index=False):
        (year, *rest) = t
        if year == year_to_check:
            expected.add(
                Sku.from_tuple((dt.datetime(year=year, month=1, day=1), *rest))
            )

    assert set(demand.demand_for_date(year_to_check)) == expected
