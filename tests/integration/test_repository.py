from src.adapters.repository import Sqlite3Repository
import src.services.services as services
import pytest
import sqlite3


@pytest.fixture
def test_db():
    session = sqlite3.connect(":memory:")
    session.execute(
        "CREATE TABLE IF NOT EXISTS scenarios (src, scenario_name, year, image, config, region, market, country_id, product, product_id, doses, site, site_code, asset_key, percent_utilization)"
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.parametrize("strategy", ["vpack", "vfn"])
def test_repository_can_save_a_sku(allocated_sku, test_db, strategy):

    session = test_db

    repo = Sqlite3Repository(test_db)

    services.save_scenario(strategy, "test", [allocated_sku], repo)

    session.commit()

    row = session.execute(
        "SELECT * FROM scenarios WHERE src == ?", (strategy,)
    ).fetchall()[0]

    assert "test" == row["scenario_name"]
    assert allocated_sku.date.year == row["year"]
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


@pytest.mark.parametrize("strategy", ["vpack", "vfn"])
def test_repository_can_delete_a_sku(allocated_sku, test_db, strategy):
    session = test_db

    repo = Sqlite3Repository(test_db)

    data = {"src": strategy, "scenario_name": "test", **allocated_sku.to_dict()}

    repo.add("scenarios", data)
    session.commit()

    data = {"src": strategy, "scenario_name": "test"}

    repo.delete("scenarios", data)
    session.commit()

    row = session.execute(
        "SELECT * FROM scenarios WHERE src == ?", (strategy,)
    ).fetchall()

    assert row == []


@pytest.mark.parametrize("strategy", ["vpack", "vfn"])
def test_repository_can_get_scenario_names(allocated_sku, test_db, strategy):
    session = test_db

    repo = Sqlite3Repository(test_db)

    data = {"src": strategy, "scenario_name": "test", **allocated_sku.to_dict()}

    repo.add("scenarios", data)
    session.commit()
    data = {"src": strategy, "scenario_name": "test2", **allocated_sku.to_dict()}
    repo.add("scenarios", data)
    session.commit()

    rows = repo.select("scenarios").fetchall()

    print(rows)

    assert "test" == rows[0]["scenario_name"]
    assert "test2" == rows[1]["scenario_name"]


@pytest.mark.parametrize("strategy", ["vpack", "vfn"])
def test_repository_can_get_scenario_data(allocated_sku, test_db, strategy):
    session = test_db

    repo = Sqlite3Repository(test_db)

    data = {"src": strategy, "scenario_name": "test", **allocated_sku.to_dict()}

    repo.add("scenarios", data)
    session.commit()

    row = repo.select(
        "scenarios", {"src": strategy, "scenario_name": "test"}
    ).fetchall()[0]

    assert "test" == row["scenario_name"]
    assert allocated_sku.date.year == row["year"]
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
