from src.domain.relational_data import RunRates
from src.domain.approvals import VpackApprovals
from src.domain.priorities import GeneralPriorities, Priorities
from src.domain.optimizer import VpackOptimizerBuilder
from src.domain.models import Sku, Asset
import pytest
import datetime as dt

approvals = VpackApprovals(
    {
        ("Haarlem-V11", "LA", "SYRINGE", "10x", "Gardasil 9"): (
            dt.datetime(year=2022, month=1, day=1),
            dt.datetime(year=2031, month=1, day=1),
        )
    }
)

priority_schema = GeneralPriorities(
    {"Haarlem-V11": 1, ("Haarlem-V11", "10x"): 10, ("Haarlem-V11", "10x"): 10},
)

priorities = Priorities(priority_schema, approvals)

run_rates = RunRates({("Haarlem-V11", "SYRINGE", "10x"): (5, 1.5)})

unmet_demand = Asset(
    "Unmet Demand",
    "UNMT",
    "ZUNMET",
    "N/A",
    "N/A",
    dt.datetime(year=2022, month=1, day=1),
    {},
)


def test_vpack_optimization(asset, sku):
    optimizer = VpackOptimizerBuilder("B", None).build_optimizer()
    optimizer.demand.data = {sku}
    optimizer.priorities = priorities
    optimizer.run_rates = run_rates
    optimizer.assets = {asset}

    expected_output = sorted(
        [
            Sku(
                **{
                    "date": dt.datetime(year=2022, month=1, day=1),
                    "image": "SYRINGE",
                    "config": "10x",
                    "region": "LA",
                    "market": "Peru",
                    "country_id": "PE",
                    "product": "Gardasil 9",
                    "product_id": "GSL",
                    "doses": 28757,
                    "batches": 10.0,
                    "allocated_to": asset,
                    "percent_utilization": 1.0,
                }
            ),
            Sku(
                **{
                    "date": dt.datetime(year=2022, month=1, day=1),
                    "image": "SYRINGE",
                    "config": "10x",
                    "region": "LA",
                    "market": "Peru",
                    "country_id": "PE",
                    "product": "Gardasil 9",
                    "product_id": "GSL",
                    "doses": 21243,
                    "batches": 10.0,
                    "allocated_to": unmet_demand,
                    "percent_utilization": 0,
                }
            ),
        ]
    )

    optimizer.optimize_period(2022)

    for idx, sku in enumerate(sorted(list(optimizer.allocated_skus))):
        assert sku.date == expected_output[idx].date
        assert sku.image == expected_output[idx].image
        assert sku.config == expected_output[idx].config
        assert sku.region == expected_output[idx].region
        assert sku.market == expected_output[idx].market
        assert sku.country_id == expected_output[idx].country_id
        assert sku.product == expected_output[idx].product
        assert sku.product_id == expected_output[idx].product_id
        assert sku.doses == expected_output[idx].doses
        assert sku.batches == expected_output[idx].batches
        assert sku.allocated_to == expected_output[idx].allocated_to
        assert sku.percent_utilization == pytest.approx(
            expected_output[idx].percent_utilization
        )


def test_vfn_optimization():
    pass
