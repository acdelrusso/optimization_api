from src.domain.relational_data import RunRates
from src.domain.approvals import VpackApprovals
from src.domain.priorities import GeneralPriorities, Priorities
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


def test_vpack_approvals_return_true(sku, asset):
    approvals = VpackApprovals(
        {
            ("Haarlem-V11", "LA", "SYRINGE", "10x", "Gardasil 9"): (
                dt.datetime(year=2022, month=1, day=1),
                dt.datetime(year=2031, month=1, day=1),
            )
        }
    )

    assert approvals.get_approval(sku, asset) is True

    approvals = VpackApprovals(
        {
            ("Haarlem-V11", "LA", "SYRINGE", "10x", "All"): (
                dt.datetime(year=2022, month=1, day=1),
                dt.datetime(year=2031, month=1, day=1),
            )
        }
    )

    assert approvals.get_approval(sku, asset) is True


def test_vpack_approvals_return_false(sku, asset):
    approvals = VpackApprovals({})

    assert approvals.get_approval(sku, asset) is False

    approvals.update(
        {
            ("Haarlem-V11", "LA", "SYRINGE", "10x", "Gardasil 9"): (
                dt.datetime(year=2025, month=1, day=1),
                dt.datetime(year=2031, month=1, day=1),
            )
        }
    )

    assert approvals.get_approval(sku, asset) is False


def test_priorities_calculates_correctly(sku, asset):
    approvals = VpackApprovals({})

    prioritization_schema = GeneralPriorities(
        {"Haarlem-V11": 1, ("Haarlem-V11", "10x"): 10, ("Haarlem-V11", "10x"): 10},
    )

    priorities = Priorities(prioritization_schema, approvals)

    assert priorities.get_priority(sku, asset) == -10

    approvals = VpackApprovals(
        {
            ("Haarlem-V11", "LA", "SYRINGE", "10x", "Gardasil 9"): (
                dt.datetime(year=2020, month=1, day=1),
                dt.datetime(year=2031, month=1, day=1),
            )
        }
    )

    prioritization_schema = GeneralPriorities(
        {"Haarlem-V11": 1, ("Haarlem-V11", "10x"): 10, ("Haarlem-V11", "10x"): 10},
    )

    priorities = Priorities(prioritization_schema, approvals)

    assert priorities.get_priority(sku, asset) == 7.9


def test_vfn_approvals_return_true():
    pass
