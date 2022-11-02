from fastapi.testclient import TestClient
from src.entry_points.main import app, get_session
import pytest
import sqlite3
import json
import datetime as dt


def override_get_session():
    session = sqlite3.connect("./src/database/e2e_test.db")
    session.execute(
        "CREATE TABLE IF NOT EXISTS scenarios (scenario_name, year, image, config, region, market, country_id, product, product_id, doses, site, site_code, asset_key, percent_utilization)"
    )
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_session] = override_get_session

client = TestClient(app)


@pytest.mark.e2e
def test_put_to_scenarios():

    data = {
        "date": dt.datetime(year=2031, month=1, day=1),
        "image": "SYRINGE",
        "config": "1x",
        "region": "EU",
        "market": "United Kingdom",
        "country_id": "GB",
        "product": "Vaqta - Adult",
        "product_id": "HPD",
        "doses": 28000,
        "batches": 1.793,
        "allocated_to": {
            "name": "Haarlem-V10",
            "site_code": 1014,
            "asset_key": "W40V10_1014_008",
            "type": "Internal",
            "image": "SYRINGE",
            "capacities": {
                "2022": 5760.0,
                "2023": 5760.0,
                "2024": 5760.0,
                "2025": 5760.0,
                "2026": 5760.0,
                "2027": 5760.0,
                "2028": 5760.0,
                "2029": 5760.0,
                "2030": 5760.0,
                "2031": 5760.0,
            },
        },
        "percent_utilization": 0.002230150462962963,
    }

    scenario_name = "TestScenario"

    r = client.put(
        f"/scenarios?scenario_name={scenario_name}",
        data=json.dumps([data], default=str),
    )

    assert r.status_code == 201

    r = client.get("/scenarios")

    assert r.status_code == 200
    assert r.json()[0]["scenario_name"] == scenario_name

    r = client.delete(f"/scenarios/{scenario_name}")

    assert r.status_code == 204

    r = client.get("/scenarios")

    assert r.status_code == 200
    assert r.json() == []
