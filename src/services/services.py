from src.domain.optimizer import OptimizerBuilder, OptimizerDirector
from src.adapters.repository import AbstractRepository
from src.domain.models import Sku


def run_scenario(demand_scenario: str, file) -> list[dict]:
    builder = OptimizerBuilder(demand_scenario, "General Priorities", file)
    optimizer = OptimizerDirector(builder).build_optimizer("vpack")

    optimizer.optimize()

    return list(optimizer.allocated_skus)


def save_scenario(scenario_name: str, skus: list[Sku], repo: AbstractRepository):
    try:
        repo.add(skus, scenario_name)
    except Exception as error:
        print(f"Error saving scenario to database: {error}")
