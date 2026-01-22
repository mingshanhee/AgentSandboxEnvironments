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
        flask_app = create_app(runner, environments={"test-env": {"container_type": "local"}})
        yield flask_app

def test_start_instance(app):
    client = TestClient(app)
    resp = client.post("/start_instance", json={"container_name": "test-env", "run_id": "run-1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["instance_id"] == "run-1"

def test_execute_command(app):
    client = TestClient(app)
    # Must start first to record in runner
    client.post("/start_instance", json={"container_name": "test-env", "run_id": "run-1"})
    
    resp = client.post("/execute_command", json={"run_id": "run-1", "cmd": "whoami"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["result"]["output"] == "api mocked"

def test_multiple_instances_same_container(app):
    client = TestClient(app)
    # Start two instances of same container with different run_ids
    resp1 = client.post("/start_instance", json={"container_name": "test-env", "run_id": "run-1"})
    resp2 = client.post("/start_instance", json={"container_name": "test-env", "run_id": "run-2"})
    
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    
    # Verify both are running
    resp_resources = client.get("/get_available_resources")
    assert resp_resources.json()["instances"] == 0 # 2 instances used

    # Execute on run-1
    resp_exec1 = client.post("/execute_command", json={"run_id": "run-1", "cmd": "cmd1"})
    assert resp_exec1.status_code == 200
    
    # Execute on run-2
    resp_exec2 = client.post("/execute_command", json={"run_id": "run-2", "cmd": "cmd2"})
    assert resp_exec2.status_code == 200

def test_resource_limits_api(app):
    client = TestClient(app)
    # available: 2. Start 1.
    client.post("/start_instance", json={"container_name": "test-env", "run_id": "run-1"})
    
    resp = client.get("/get_available_resources")
    assert resp.json()["instances"] == 1
    
    # Start 2nd
    client.post("/start_instance", json={"container_name": "test-env-2", "run_id": "run-2", "environment_config": {"container_type": "local"}})
    
    resp = client.get("/get_available_resources")
    assert resp.json()["instances"] == 0
    
    # Start 3rd -> Should fail 500
    resp = client.post("/start_instance", json={"container_name": "test-env-3", "run_id": "run-3", "environment_config": {"container_type": "local"}})
    assert resp.status_code == 500 
    
    # Close one
    client.post("/close_instance", json={"run_id": "run-1"})
    resp = client.get("/get_available_resources")
    assert resp.json()["instances"] == 1
