from src.domain.models import Sku, Asset
import pytest
import datetime as dt

# Sku Fixtures


@pytest.fixture
def sku_values():
    return {
        "date": dt.datetime(year=2022, month=1, day=1),
        "material_number": "12345678",
        "image": "SYRINGE",
        "config": "10x",
        "region": "LA",
        "market": "Peru",
        "country_id": "PE",
        "product": "Gardasil 9",
        "product_id": "GSL",
        "doses": 50000,
        "batches": 10.0,
        "allocated_to": None,
        "percent_utilization": None,
    }


@pytest.fixture
def allocated_sku(asset, sku_values):
    sku_values["allocated_to"] = asset
    sku_values["percent_utilization"] = 1.0
    return Sku(**sku_values)


@pytest.fixture
def sku(sku_values):
    return Sku(**sku_values)


# Asset Fixtures


@pytest.fixture
def asset_values():
    return {
        "name": "Haarlem-V11",
        "site_code": "1014",
        "asset_key": "W40V11_1014_008",
        "type": "Internal",
        "image": "SYRINGE",
        "launch_date": dt.datetime(2022, 1, 1),
        "capacities": {2022: 5760, 2023: 5760, 2024: 5760},
    }


@pytest.fixture
def asset(asset_values):
    return Asset(**asset_values)
