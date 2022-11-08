from src.domain.optimizer import OptimizerBuilder, OptimizerDirector
from src.adapters.repository import AbstractRepository
from src.domain.models import Sku


def run_scenario(
    demand_scenario: str, prioritization_schema: str, file, strategy: str
) -> list[dict]:
    builder = OptimizerBuilder(demand_scenario, prioritization_schema, file)
    optimizer = OptimizerDirector(builder).build_optimizer(strategy)

    optimizer.optimize()

    return list(optimizer.allocated_skus)


def save_scenario(strategy: str, scenario_name: str, skus: list[Sku], repo: AbstractRepository):
    try:
        repo.add(skus, scenario_name, strategy)
    except Exception as error:
        print(f"Error saving scenario to database: {error}")
