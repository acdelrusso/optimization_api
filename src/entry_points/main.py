from fastapi import FastAPI, File, Response, status
from ..services import services
from . import schemas
import src.adapters.repository as repository
from typing import Optional
import sqlite3

app = FastAPI()


def get_session():
    return sqlite3.connect("./src/database/data.db")


@app.post("/scenarios", response_model=list[schemas.Sku])
def run_scenario(demand: str, file: Optional[bytes] = File(None)):
    return services.run_scenario(demand, file)


@app.put("/scenarios")
def save_last_run_scenario(scenario_name: str, data: list[schemas.Sku]):
    session = get_session()
    repo = repository.Sqlite3Repository(session)
    services.save_scenario(scenario_name, data, repo)
    session.commit()

    return Response(status_code=status.HTTP_201_CREATED)


@app.get("/scenarios/{scenario_name}")
def get_scenario_data(scenario_name: str):
    session = get_session()
    repo = repository.Sqlite3Repository(session)
    return repo.get(scenario_name)


@app.delete("/scenarios/{scenario_name}")
def delete_scenario_data(scenario_name: str):
    session = get_session()
    repo = repository.Sqlite3Repository(session)
    return repo.delete(scenario_name)


@app.get("/scenarios")
def get_all_scenarios_in_db():
    session = get_session()
    repo = repository.Sqlite3Repository(session)
    return repo.get_all()
