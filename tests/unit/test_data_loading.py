import os
import datetime as dt
import pytest
from src.domain.optimizer import OptimizerBuilder
from src.domain.models import Sku
from src.domain.priorities import GeneralPriorities

my_path = os.path.abspath(os.path.dirname(__file__))
path_to_standard_input = os.path.join(my_path, "../../src/inputs/testing.xlsx")

test_object = OptimizerBuilder("B", "General Priorities", path_to_standard_input)


def test_lrop_loads():
    demand = test_object._load_demand("B")

    for sku in demand.data:
        assert sku.date == dt.datetime(year=2030, month=1, day=1)
        assert sku.image == "SYRINGE"
        assert sku.config == "10x"
        assert sku.region == "EEMEA"
        assert sku.market == "Not Specified"
        assert sku.country_id == "#"
        assert sku.product == "MK1654 RSV MaB"
        assert sku.product_id == "RSM"
        assert sku.doses == 18200
        assert sku.batches == 1.4


def test_assets_load():
    assets = test_object._load_assets()

    for asset in assets:
        assert asset.name == "Haarlem-V11"
        assert asset.site_code == "1014"
        assert asset.asset_key == "W40V11_1014_008"
        assert asset.type == "Internal"
        assert asset.image == "SYRINGE"
        assert asset.capacities == {
            2022: 0,
            2023: 0,
            2024: 0,
            2025: 2880,
            2026: 5760,
            2027: 5760,
            2028: 5760,
            2029: 5760,
            2030: 5760,
            2031: 5760,
        }
        assert asset.launch_date == dt.datetime(year=2020, month=1, day=1)


def test_vpack_approvals_load(sku_values, asset):
    test_object.years = list(range(2022, 2032))
    approvals = test_object._load_approvals("vpack")

    sku = Sku(**sku_values)

    assert approvals.get_approval(sku, asset) is False

    sku_values["config"] = "10x combi"
    sku_values["date"] = dt.datetime(year=2027, month=1, day=1)
    sku_values["region"] = "EEMEA"

    sku = Sku(**sku_values)

    assert approvals.get_approval(sku, asset) is True


def test_prioritization_schema_is_correct():
    assert isinstance(test_object._get_prioritization_schema(), GeneralPriorities)


def test_priorities_load(sku_values, asset):
    priorities = test_object._load_priorities("vpack")

    sku = Sku(**sku_values)

    assert priorities.get_priority(sku, asset) == -10

    sku_values["config"] = "10x combi"
    sku_values["date"] = dt.datetime(year=2027, month=1, day=1)
    sku_values["region"] = "EEMEA"

    sku = Sku(**sku_values)

    assert priorities.get_priority(sku, asset) == 8.4


def test_run_rates_load(sku, asset):
    run_rates = test_object._load_run_rates()

    assert run_rates.get_utilization(sku, asset, 1.0) == pytest.approx(0.0035, rel=0.1)
