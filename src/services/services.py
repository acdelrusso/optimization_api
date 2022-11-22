from src.domain.optimizer import OptimizerBuilder
from src.adapters.repository import AbstractRepository
from src.domain.models import Sku
from fastapi import HTTPException, status


def build_optimizer(
    demand_scenario: str, prioritization_schema: str, file, strategy: str
) -> list[dict]:

    return OptimizerBuilder(
        demand_scenario, prioritization_schema, file
    ).build_optimizer(strategy)


def save_scenario(
    strategy: str, scenario_name: str, skus: list[Sku], repo: AbstractRepository
):
    data = [sku.to_dict() for sku in skus]
    try:
        repo.add_many("scenarios", strategy, scenario_name, data)
    except Exception as error:
        print(error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"error saving to local DB: {error}",
        ) from error


def send_to_aws(
    strategy: str, scenario_name: str, skus: list[Sku], repo: AbstractRepository
):
    try:
        data = [sku.to_aws() for sku in skus]
        repo.add_many("sam_py_model.vfn_vpac_cap_vol", strategy, scenario_name, data)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"error pushing to aws: {error}",
        ) from error
