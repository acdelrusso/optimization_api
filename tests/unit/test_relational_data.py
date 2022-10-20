from src.domain.relational_data import RunRates, Approvals, Priorities
from src.domain.asset import Asset
from src.domain.sku import Sku
import pytest


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
        "capacities": {2022: 0, 2023: 5760, 2024: 5760},
    }
    asset = Asset(**asset_values)

    run_rates = RunRates({("Haarlem-V11", "SYRINGE", "10x"): (9720, 1.5)})

    utilization = run_rates.get_utilization(sku, asset, 1)

    assert utilization == 1000000


def test_approvals_return_true(sku, asset):
    approvals = Approvals(
        {("Haarlem-V11", "LA", "SYRINGE", "10x", "Gardasil 9"): (2022, 2031)}
    )

    assert approvals.get_approval(sku, asset) is True

    approvals = Approvals(
        {("Haarlem-V11", "LA", "SYRINGE", "10x", "All"): (2022, 2031)}
    )

    assert approvals.get_approval(sku, asset) is True


def test_approvals_return_false(sku, asset):
    approvals = Approvals({})

    assert approvals.get_approval(sku, asset) is False

    approvals.update(
        {("Haarlem-V11", "LA", "SYRINGE", "10x", "Gardasil 9"): (2025, 2031)}
    )

    assert approvals.get_approval(sku, asset) is False


def test_priorities_calculates_correctly(sku, asset):
    approvals = Approvals({})

    priorities = Priorities(
        {"Haarlem-V11": 1, ("Haarlem-V11", "10x"): 10, ("Haarlem-V11", "10x"): 10},
        approvals,
    )

    assert priorities.get_priority(sku, asset) == -10

    approvals = Approvals(
        {("Haarlem-V11", "LA", "SYRINGE", "10x", "Gardasil 9"): (2020, 2031)}
    )

    priorities = Priorities(
        {"Haarlem-V11": 1, ("Haarlem-V11", "10x"): 10, ("Haarlem-V11", "10x"): 10},
        approvals,
    )

    assert priorities.get_priority(sku, asset) == 7.9
