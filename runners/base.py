from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseRunner(ABC):
    """Abstract base class for runners."""

    def __init__(self, max_resources: Dict[str, Any]):
        self.max_resources = max_resources
        self.allocated_resources: Dict[str, Any] = {key: 0 for key in max_resources}
        self.running_instances: Dict[str, Any] = {}

    @abstractmethod
    def start_instance(self, container_name: str, run_id: str, environment_config: Dict[str, Any]) -> str:
        """Starts an instance with the given config and run ID. Returns the run ID."""
        pass

    @abstractmethod
    def execute_command(self, run_id: str, cmd: str) -> Dict[str, Any]:
        """Executes a command in the specified run ID."""
        pass

    @abstractmethod
    def close_instance(self, run_id: str) -> None:
        """Closes the specified run ID."""
        pass

    def get_available_resources(self) -> Dict[str, Any]:
        """Returns the available resources."""
        return {
            key: self.max_resources[key] - self.allocated_resources.get(key, 0)
            for key in self.max_resources
        }

    def _check_resources(self, required_resources: Dict[str, Any]) -> bool:
        """Checks if enough resources are available."""
        available = self.get_available_resources()
        for key, value in required_resources.items():
            if key in self.max_resources and available.get(key, 0) < value:
                return False
        return True

    def _allocate_resources(self, resources: Dict[str, Any]):
        """Allocates resources."""
        for key, value in resources.items():
            if key in self.max_resources:
                self.allocated_resources[key] = self.allocated_resources.get(key, 0) + value

    def _release_resources(self, resources: Dict[str, Any]):
        """Releases resources."""
        for key, value in resources.items():
            if key in self.max_resources:
                self.allocated_resources[key] = max(0, self.allocated_resources.get(key, 0) - value)
