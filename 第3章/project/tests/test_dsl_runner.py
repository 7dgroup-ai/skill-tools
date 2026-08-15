import httpx
from pathlib import Path

import pytest

from clients.http_client import HttpClient
from dsl.loader import load_scenario
from dsl.runner import ScenarioRunner, ScenarioError
from tests.fake_store import make_transport

SCENARIOS = Path(__file__).parent.parent / "scenarios"


@pytest.fixture()
def client():
    c = HttpClient("http://fake", transport=make_transport())
    yield c
    c.close()


def test_load_scenario_valid():
    scenario = load_scenario(SCENARIOS / "login_flow.yaml")
    assert scenario["name"] == "login_flow"
    assert scenario["steps"][0]["request"]["path"] == "/api/login"


def test_login_flow_runs(client):
    runner = ScenarioRunner(client, context={"user": "u_1001", "password": "pass_1001"})
    results = runner.run_file(str(SCENARIOS / "login_flow.yaml"))
    assert all(r.ok for r in results)
    assert len(runner.ctx["token"]) >= 20


def test_order_flow_runs(client):
    runner = ScenarioRunner(client, context={
        "user": "u_1001", "password": "pass_1001", "goods_id": "g_2001"})
    results = runner.run_file(str(SCENARIOS / "order_flow.yaml"))
    assert all(r.ok for r in results)
    assert runner.ctx.get("order_id")


def test_order_flow_fails_on_bad_user(client):
    runner = ScenarioRunner(client, context={
        "user": "nobody", "password": "wrong", "goods_id": "g_2001"})
    with pytest.raises(ScenarioError):
        runner.run_file(str(SCENARIOS / "order_flow.yaml"))
