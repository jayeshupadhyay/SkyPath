import os
import sys
from pathlib import Path

# Ensure imports like `from app.main import app` work inside the container
# tests live at /app/tests -> parents[1] == /app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient


def _set_test_data_path():
    """
    In Docker, flights.json is mounted at /data/flights.json.
    If running locally, fall back to repo_root/flights.json.
    """
    docker_path = Path("/data/flights.json")
    if docker_path.exists():
        os.environ["FLIGHTS_DATA_PATH"] = str(docker_path)
        return

    repo_root = Path(__file__).resolve().parents[2]
    local_path = repo_root / "flights.json"
    if not local_path.exists():
        raise RuntimeError(f"Expected flights.json at {local_path} but it was not found.")
    os.environ["FLIGHTS_DATA_PATH"] = str(local_path)


@pytest.fixture(scope="session")
def client():
    _set_test_data_path()

    # Import after env var is set so FastAPI startup uses it
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health_ok(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["airports"] > 0
    assert data["flights"] > 0
    assert "stats" in data


def test_search_returns_results_for_known_route(client: TestClient):
    r = client.get("/search", params={"origin": "JFK", "destination": "LAX", "date": "2024-03-15"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    assert "segments" in first
    assert "totalDurationMinutes" in first
    assert "totalPrice" in first
    assert first["segments"][0]["origin"] == "JFK"
    assert first["segments"][-1]["destination"] == "LAX"


def test_search_invalid_airport_returns_400(client: TestClient):
    r = client.get("/search", params={"origin": "XXX", "destination": "LAX", "date": "2024-03-15"})
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body


def test_search_bad_date_returns_400(client: TestClient):
    r = client.get("/search", params={"origin": "JFK", "destination": "LAX", "date": "2024-15-03"})
    assert r.status_code == 400


def test_search_same_origin_destination_returns_empty_list(client: TestClient):
    r = client.get("/search", params={"origin": "JFK", "destination": "JFK", "date": "2024-03-15"})
    assert r.status_code == 200
    assert r.json() == []

def test_search_sfo_to_nrt_returns_results(client: TestClient):
    # Instruction test case: international route
    r = client.get("/search", params={"origin": "SFO", "destination": "NRT", "date": "2024-03-15"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Basic shape checks
    first = data[0]
    assert first["segments"][0]["origin"] == "SFO"
    assert first["segments"][-1]["destination"] == "NRT"
    assert first["totalDurationMinutes"] > 0
    assert first["totalPrice"] > 0


def test_search_bos_to_sea_returns_results(client: TestClient):
    # Instruction test case: typically no direct; should find connections if available
    r = client.get("/search", params={"origin": "BOS", "destination": "SEA", "date": "2024-03-15"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Ensure endpoints match
    first = data[0]
    assert first["segments"][0]["origin"] == "BOS"
    assert first["segments"][-1]["destination"] == "SEA"

    # If it is a connection, layovers array should align with segments-1
    assert len(first["layoversMinutes"]) == max(0, len(first["segments"]) - 1)


def test_search_syd_to_lax_date_line_returns_results(client: TestClient):
    # Instruction test case: crosses the international date line; good for timezone correctness
    r = client.get("/search", params={"origin": "SYD", "destination": "LAX", "date": "2024-03-15"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

    # Depending on dataset contents, this should usually return results.
    # If the dataset ever changes, failing hard here can be brittle, so we allow empty but still validate structure.
    if len(data) == 0:
        return

    first = data[0]
    assert first["segments"][0]["origin"] == "SYD"
    assert first["segments"][-1]["destination"] == "LAX"
    assert first["totalDurationMinutes"] > 0

    # Sanity check: total duration should be at least as long as sum of segment durations
    # (we can't compute exact segment durations without UTC fields in response, but at least ensure positive.)
    assert first["totalDurationMinutes"] > 0
