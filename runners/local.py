import logging
import time
from typing import Any, Dict
from runners.base import BaseRunner

try:
    from environments import get_environment
except ImportError:
    # For testing/when not running from root
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from environments import get_environment

logger = logging.getLogger(__name__)

class LocalRunner(BaseRunner):
    """Runner for local execution."""

    def __init__(self, max_resources: Dict[str, Any]):
        super().__init__(max_resources)

    def start_instance(self, request_params: Dict[str, Any]) -> str:
        """Starts a local environment instance."""
        # Extract parameters
        run_id = request_params["run_id"]
        container_image = request_params["container_image"]
        needed_resources = request_params.get("resources", {"instances": 1})
        
        # Check resources
        if not self._check_resources(needed_resources):
            raise RuntimeError(f"Not enough resources. Available: {self.get_available_resources()}")

        try:
            # Create environment with all request parameters
            env = get_environment(request_params)
            # Some environments might start automatically in __init__, others might need explicit start if added
            # But based on docker.py, _start_container is called in __init__.
            self.running_instances[run_id] = {
                "container_image": container_image,
                "env": env,
                "resources": needed_resources,
                "created_at": time.time(),
                "updated_at": None,
                "num_cmd": 0
            }
            self._allocate_resources(needed_resources)
            return run_id
        except Exception as e:
            logger.error(f"Failed to start instance for container {container_image}, run {run_id}: {e}")
            raise

    def execute_command(self, run_id: str, cmd: str) -> Dict[str, Any]:
        """Executes a command in the local instance."""
        if run_id not in self.running_instances:
            raise KeyError(f"Run ID {run_id} not found.")
        
        env = self.running_instances[run_id]["env"]
        # Assuming env has an execute method as seen in docker.py
        result = env.execute(cmd)
        self.running_instances[run_id]["num_cmd"] += 1
        self.running_instances[run_id]["updated_at"] = time.time()
        return result

    def close_instance(self, run_id: str) -> None:
        """Closes the local instance."""
        if run_id not in self.running_instances:
            raise KeyError(f"Run ID {run_id} not found.")

        instance_data = self.running_instances[run_id]
        env = instance_data["env"]
        resources = instance_data["resources"]
        
        if hasattr(env, "cleanup"):
            env.cleanup()
        elif hasattr(env, "close"):
            env.close()
            
        self._release_resources(resources)
        del self.running_instances[run_id]
