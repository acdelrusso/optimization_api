import os
import datetime as dt
import pandas as pd
import pytest
from src.domain.data_loaders import (
    LROPloader,
    AssetLoader,
    ApprovalsLoader,
    PrioritiesLoader,
    RunRatesLoader,
)
from src.domain.models import Sku
from src.domain.priorities import GeneralPriorities, VariableCosts

my_path = os.path.abspath(os.path.dirname(__file__))
path_to_standard_input = os.path.join(my_path, "../../src/inputs/testing.xlsx")

data = pd.read_excel(path_to_standard_input, sheet_name=None)


def test_lrop_loads():
    lrop, years = LROPloader().load("B", data)

    assert lrop["Year"][0] == 2030
    assert lrop["Material_Number"][0] == 1234567
    assert lrop["Image"][0] == "SYRINGE"
    assert lrop["Config"][0] == "10x"
    assert lrop["Region"][0] == "EEMEA"
    assert lrop["Market"][0] == "Not Specified"
    assert lrop["Country_ID"][0] == "#"
    assert lrop["Product"][0] == "MK1654 RSV MaB"
    assert lrop["Product_ID"][0] == "RSM"
    assert lrop["Total"][0] == 18200
    assert lrop["Batches"][0] == 1.4


def test_assets_load():
    assets = AssetLoader().load(data)

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
    approvals = ApprovalsLoader().load(data, "vpack", list(range(2022, 2032)))

    sku = Sku(**sku_values)

    assert approvals.get_approval(sku, asset) is False

    sku_values["config"] = "10x combi"
    sku_values["date"] = dt.datetime(year=2027, month=1, day=1)
    sku_values["region"] = "EEMEA"

    sku = Sku(**sku_values)

    assert approvals.get_approval(sku, asset) is True


def test_prioritization_schema_is_correct():
    assert isinstance(
        PrioritiesLoader()
        .load(data, "vpack", "General Priorities", list(range(2022, 2032)))
        .prioritization_scheme,
        GeneralPriorities,
    )


def test_priorities_load(sku_values, asset):
    priorities = PrioritiesLoader().load(
        data, "vpack", "General Priorities", list(range(2022, 2032))
    )

    sku = Sku(**sku_values)

    assert priorities.get_priority(sku, asset) == -10

    sku_values["config"] = "10x combi"
    sku_values["date"] = dt.datetime(year=2027, month=1, day=1)
    sku_values["region"] = "EEMEA"

    sku = Sku(**sku_values)

    assert priorities.get_priority(sku, asset) == 8.4


def test_run_rates_load(sku, asset):
    run_rates = RunRatesLoader().load(data)

    assert run_rates.get_utilization(sku, asset, 1.0) == pytest.approx(0.0035, rel=0.1)
