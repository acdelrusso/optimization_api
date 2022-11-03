from src.domain.relational_data import RunRates
from src.domain.models import Asset
import pytest
import datetime as dt


def test_run_rates_returns_rate(sku, asset):
    run_rates = RunRates({("Haarlem-V11", "SYRINGE", "10x"): (9720, 1.5)})

    utilization = run_rates.get_utilization(sku, asset, 1)

    assert utilization == pytest.approx(0.003, rel=1e1)


def test_undefined_rate_returns_large_number(sku):
    asset_values = {
        "name": "Haarlem-V11",
        "site_code": "1014",
        "asset_key": "W40V11_1014_008",
        "type": "Internal",
        "image": "SYRINGE",
        "launch_date": dt.datetime(2022, 1, 1),
        "capacities": {2022: 0, 2023: 5760, 2024: 5760},
    }
    asset = Asset(**asset_values)

    run_rates = RunRates({("Haarlem-V11", "SYRINGE", "10x"): (9720, 1.5)})

    utilization = run_rates.get_utilization(sku, asset, 1)

    assert utilization == 1000000
