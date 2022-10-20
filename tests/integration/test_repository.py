from src.adapters.repository import Sqlite3Repository
from src.domain.sku import Sku
import sqlite3
import pytest


@pytest.fixture
def test_db():
    session = sqlite3.connect("./src/database/test.db")
    session.execute(
        "CREATE TABLE scenarios (scenario_name, year, image, config, region, market, country_id, product, product_id, doses, site, site_code, asset_key, percent_utilization)"
    )
    session.commit()
    try:
        yield session
    finally:
        session.execute("DROP TABLE scenarios")
        session.commit()
        session.close()


def test_repository_can_save_a_sku(allocated_sku, test_db):

    session = test_db

    repo = Sqlite3Repository(test_db)

    repo.add([allocated_sku], "test")
    session.commit()

    row = session.execute("SELECT * FROM scenarios").fetchall()[0]

    assert "test" == row["scenario_name"]
    assert allocated_sku.year == row["year"]
    assert allocated_sku.image == row["image"]
    assert allocated_sku.config == row["config"]
    assert allocated_sku.region == row["region"]
    assert allocated_sku.market == row["market"]
    assert allocated_sku.country_id == row["country_id"]
    assert allocated_sku.product == row["product"]
    assert allocated_sku.product_id == row["product_id"]
    assert allocated_sku.doses == row["doses"]
    assert allocated_sku.allocated_to.name == row["site"]
    assert allocated_sku.allocated_to.site_code == row["site_code"]
    assert allocated_sku.allocated_to.asset_key == row["asset_key"]
    assert allocated_sku.percent_utilization == row["percent_utilization"]


def test_repository_can_delete_a_sku(allocated_sku, test_db):
    session = test_db

    repo = Sqlite3Repository(test_db)

    repo.add([allocated_sku], "test")
    session.commit()

    repo.delete("test")
    session.commit()

    row = session.execute("SELECT * FROM scenarios").fetchall()

    assert row == []


def test_repository_can_get_scenario_names(allocated_sku, test_db):
    session = test_db

    repo = Sqlite3Repository(test_db)

    repo.add([allocated_sku], "test")
    repo.add([allocated_sku], "test2")
    session.commit()

    rows = repo.get_all()

    assert {"scenario_name": "test"} in rows
    assert {"scenario_name": "test2"} in rows

def test_repository_can_get_scenario_data(allocated_sku, test_db):
    session = test_db

    repo = Sqlite3Repository(test_db)

    repo.add([allocated_sku], "test")
    session.commit()

    row = repo.get("test")[0]

    assert "test" == row["scenario_name"]
    assert allocated_sku.year == row["year"]
    assert allocated_sku.image == row["image"]
    assert allocated_sku.config == row["config"]
    assert allocated_sku.region == row["region"]
    assert allocated_sku.market == row["market"]
    assert allocated_sku.country_id == row["country_id"]
    assert allocated_sku.product == row["product"]
    assert allocated_sku.product_id == row["product_id"]
    assert allocated_sku.doses == row["doses"]
    assert allocated_sku.allocated_to.name == row["site"]
    assert allocated_sku.allocated_to.site_code == row["site_code"]
    assert allocated_sku.allocated_to.asset_key == row["asset_key"]
    assert allocated_sku.percent_utilization == row["percent_utilization"]