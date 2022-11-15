from fastapi import Depends, FastAPI, File, Response, status
from ..services import services
from ..domain import models
import src.adapters.repository as repository
from typing import Optional
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import src.config as config
import uvicorn
import multiprocessing
import itertools

app = FastAPI()


database_source = "sqlite"


def get_session():
    if database_source == "aws":
        creds = config.get_aws_creds()
        return psycopg2.connect(
            host=config.settings.db_endpoint,
            port=config.settings.db_port,
            database=config.settings.db_name,
            user=creds["DbUser"],
            password=creds["DbPassword"],
            cursor_factory=RealDictCursor,
        )
    return sqlite3.connect("./src/database/data.db")


@app.post("/scenarios/{strategy}", response_model=list[models.Sku])
def run_scenario(
    strategy: str,
    demand: str,
    prioritization_schema: str,
    file: Optional[bytes] = File(None),
):
    optimizer = services.build_optimizer(demand, prioritization_schema, file, strategy)

    with multiprocessing.Pool() as pool:
        if strategy == "vpack":
            results = pool.map(optimizer.optimize_period, optimizer.years)
        elif strategy == "vfn":
            results = pool.starmap(
                optimizer.optimize_period,
                itertools.product(optimizer.years, range(1, 13)),
            )

    for result in results:
        optimizer.allocated_skus.update(result)

    return list(optimizer.allocated_skus)


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
    criteria = {"src": strategy, "scenario_name": scenario_name}
    return repo.select("scenarios", criteria=criteria).fetchall()


@app.delete("/scenarios/{strategy}/{scenario_name}")
def delete_scenario_data(
    strategy: str,
    scenario_name: str,
    session: sqlite3.Connection = Depends(get_session),
):
    repo = repository.Sqlite3Repository(session)
    criteria = {"src": strategy, "scenario_name": scenario_name}
    repo.delete("scenarios", criteria)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/scenarios/{strategy}")
def get_all_scenarios_in_db(
    strategy: str,
    session: sqlite3.Connection = Depends(get_session),
):
    repo = repository.Sqlite3Repository(session)
    data = {"src": strategy}
    return repo.select(
        "scenarios", fields=["scenario_name"], criteria=data, distinct=True
    ).fetchall()


if __name__ == "__main__":
    uvicorn.run("src.entry_points.main:app", host="0.0.0.0", port=8501)
