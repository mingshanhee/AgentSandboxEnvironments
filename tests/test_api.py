from fastapi.testclient import TestClient
from api import create_app
from runners.local import LocalRunner
from unittest.mock import MagicMock, patch
import pytest

# We need to mock get_environment to avoid actual environment creation during import/runtime in LocalRunner
@pytest.fixture
def app():
    with patch("runners.local.get_environment") as mock_env:
        # Define what the mock environment returns
        env_instance = MagicMock()
        env_instance.execute.return_value = {"output": "api mocked", "returncode": 0}
        mock_env.return_value = env_instance
        
        runner = LocalRunner({"instances": 2})
        # Define some pre-existing environments config if needed, or pass empty
        flask_app = create_app(runner, environments={"test-env": {"environment_class": "local"}})
        yield flask_app

def test_start_instance(app):
    client = TestClient(app)
    resp = client.post("/start_instance", json={"container_id": "test-env"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

def test_execute_command(app):
    client = TestClient(app)
    # Must start first to record in runner
    client.post("/start_instance", json={"container_id": "test-env"})
    
    resp = client.post("/execute_command", json={"container_id": "test-env", "cmd": "whoami"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["result"]["output"] == "api mocked"

def test_resource_limits_api(app):
    client = TestClient(app)
    # available: 2. Start 1.
    client.post("/start_instance", json={"container_id": "test-env"})
    
    resp = client.get("/get_available_resources")
    assert resp.json()["instances"] == 1
    
    # Start 2nd (we can reuse ID or use new one if we pass config)
    client.post("/start_instance", json={"container_id": "test-env-2", "environment_config": {"environment_class": "local"}})
    
    resp = client.get("/get_available_resources")
    assert resp.json()["instances"] == 0
    
    # Start 3rd -> Should fail 500 (or we should handle it better as 400/503 but currently 500 string(e))
    resp = client.post("/start_instance", json={"container_id": "test-env-3", "environment_config": {"environment_class": "local"}})
    assert resp.status_code == 500 
    
    # Close one
    client.post("/close_instance", json={"container_id": "test-env"})
    resp = client.get("/get_available_resources")
    assert resp.json()["instances"] == 1
