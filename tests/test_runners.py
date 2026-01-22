import pytest
from unittest.mock import MagicMock, patch
from runners.local import LocalRunner
from runners.slurm import SlurmRunner
from environments.base import Environment

class MockEnv(Environment):
    def execute(self, cmd, cwd="", timeout=None):
        return {"output": "mocked output", "returncode": 0}
    def close(self):
        pass
    def cleanup(self):
        pass

@pytest.fixture
def mock_get_environment():
    with patch("runners.local.get_environment") as mock:
        mock.return_value = MockEnv()
        yield mock

def test_local_runner_resource_allocation(mock_get_environment):
    runner = LocalRunner({"instances": 2})
    
    # Start one instance
    runner.start_instance("inst-1", {"resources": {"instances": 1}})
    assert runner.get_available_resources()["instances"] == 1
    
    # Start second instance
    runner.start_instance("inst-2", {"resources": {"instances": 1}})
    assert runner.get_available_resources()["instances"] == 0
    
    # Fail starting third instance
    with pytest.raises(RuntimeError):
        runner.start_instance("inst-3", {"resources": {"instances": 1}})
        
    # Close one and check resources
    runner.close_instance("inst-1")
    assert runner.get_available_resources()["instances"] == 1
    
    # Clean up
    runner.close_instance("inst-2")
    assert runner.get_available_resources()["instances"] == 2

def test_local_runner_execution(mock_get_environment):
    runner = LocalRunner({"instances": 1})
    runner.start_instance("inst-1", {}) # Default 1 instance
    
    res = runner.execute_command("inst-1", "echo hello")
    assert res["output"] == "mocked output"
    assert res["returncode"] == 0
    
    runner.close_instance("inst-1")

@patch("subprocess.run")
def test_slurm_runner(mock_run):
    # Mock sbatch success
    mock_run.return_value.stdout = "12345"
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 0
    
    runner = SlurmRunner({"jobs": 5})
    runner.start_instance("slurm-1", {"resources": {"jobs": 1}})
    
    assert runner.get_available_resources()["jobs"] == 4
    
    # Mock srun success
    mock_run.return_value.stdout = "slurm output"
    res = runner.execute_command("slurm-1", "echo hello")
    assert "slurm output" in res["output"]
    
    # Close (scancel)
    runner.close_instance("slurm-1")
    assert runner.get_available_resources()["jobs"] == 5
