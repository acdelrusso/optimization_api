from fastapi import Depends, FastAPI, File, Response, status
from ..services import services
from ..domain import models
import src.adapters.repository as repository
from typing import Optional
import sqlite3

app = FastAPI()


def get_session():
    return sqlite3.connect("./src/database/data.db")


@app.post("/scenarios/{strategy}", response_model=list[models.Sku])
def run_scenario(
    strategy: str,
    demand: str,
    prioritization_schema: str,
    file: Optional[bytes] = File(None),
):
    return services.run_scenario(demand, prioritization_schema, file, strategy)


@app.put("/scenarios/{strategy}")
def save_last_run_scenario(
    strategy: str,
    scenario_name: str,
    data: list[models.Sku],
    session: sqlite3.Connection = Depends(get_session),
):
    repo = repository.Sqlite3Repository(session)
    services.save_scenario(strategy, scenario_name, data, repo)
    session.commit()

    return Response(status_code=status.HTTP_201_CREATED)


@app.get("/scenarios/{strategy}/{scenario_name}")
def get_scenario_data(
    strategy: str,
    scenario_name: str,
    session: sqlite3.Connection = Depends(get_session),
):
    repo = repository.Sqlite3Repository(session)
    return repo.get(scenario_name, strategy)


@app.delete("/scenarios/{strategy}/{scenario_name}")
def delete_scenario_data(
    strategy: str,
    scenario_name: str,
    session: sqlite3.Connection = Depends(get_session),
):
    repo = repository.Sqlite3Repository(session)
    repo.delete(scenario_name, strategy)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/scenarios/{strategy}")
def get_all_scenarios_in_db(
    strategy: str,
    session: sqlite3.Connection = Depends(get_session),
):
    repo = repository.Sqlite3Repository(session)
    return repo.get_all(strategy)
