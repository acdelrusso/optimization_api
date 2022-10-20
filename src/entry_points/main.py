from fastapi import FastAPI, File, Response, status
from ..services import services
from . import schemas
import src.adapters.repository as repository
from typing import Optional

app = FastAPI()


@app.post("/scenarios", response_model=list[schemas.Sku])
def run_scenario(demand: str, file: Optional[bytes] = File(None)):
    return services.run_scenario(demand, file)


@app.put("/scenarios")
def save_last_run_scenario(scenario_name: str, data: list[schemas.Sku]):
    repo = repository.Sqlite3Repository()
    services.save_scenario(scenario_name, data, repo)

    return Response(status_code=status.HTTP_201_CREATED)


@app.get("/scenarios/{scenario_name}")
def get_scenario_data(scenario_name: str):
    repo = repository.Sqlite3Repository()
    return repo.get(scenario_name)


@app.delete("/scenarios/{scenario_name}")
def delete_scenario_data(scenario_name: str):
    repo = repository.Sqlite3Repository()
    return repo.delete(scenario_name)


@app.get("/scenarios")
def get_all_scenarios_in_db():
    repo = repository.Sqlite3Repository()
    return repo.get_all()
