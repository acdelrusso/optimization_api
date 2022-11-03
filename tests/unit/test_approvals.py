from src.domain.approvals import VpackApprovals
import datetime as dt


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


def test_vfn_approvals_return_true():
    pass
