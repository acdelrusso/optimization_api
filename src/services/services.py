from src.domain.optimizer import OptimizerBuilder, OptimizerDirector
from src.adapters.repository import AbstractRepository, PostgresRepository
from src.domain.models import Sku
from fastapi import HTTPException, status


def build_optimizer(
    demand_scenario: str, prioritization_schema: str, file, strategy: str
) -> list[dict]:
    builder = OptimizerBuilder(demand_scenario, prioritization_schema, file)

    return OptimizerDirector(builder).build_optimizer(strategy)


def save_scenario(
    strategy: str, scenario_name: str, skus: list[Sku], repo: AbstractRepository
):
    for sku in skus:
        data = {"src": strategy, "scenario_name": scenario_name, **sku.to_dict()}
        try:
            repo.add("scenarios", data)
        except Exception as error:
            print(f"Error saving scenario to database: {error}")


def send_to_aws(
    strategy: str, scenario_name: str, skus: list[Sku], repo: PostgresRepository
):
    try:
        data = [sku.to_aws() for sku in skus]
        print("made it into repo method")
        repo.add_many("sam_py_model.vfn_vpac_cap_vol", strategy, scenario_name, data)
    except Exception as error:
        print(f"Error pushing scenario to AWS: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"error pushing to aws: {error}",
        ) from error
