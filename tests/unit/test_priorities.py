from src.domain.approvals import VpackApprovals
from src.domain.priorities import GeneralPriorities, PriorityProvider
import datetime as dt


def test_priorities_calculates_correctly(sku, asset):
    approvals = VpackApprovals({})

    prioritization_schema = GeneralPriorities(
        {"Haarlem-V11": 1, ("Haarlem-V11", "10x"): 10, ("Haarlem-V11", "10x"): 10},
    )

    priorities = PriorityProvider(prioritization_schema, approvals)

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

    priorities = PriorityProvider(prioritization_schema, approvals)

    assert priorities.get_priority(sku, asset) == 7.9
