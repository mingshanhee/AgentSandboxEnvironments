import logging
import os
import shlex
import subprocess
import uuid
from typing import Any

from pydantic import BaseModel
from environments.base import Environment


class EnrootEnvironmentConfig(BaseModel):
    image: str
    """Image to use for the container, e.g., 'ubuntu:22.04'"""
    cwd: str = "/"
    """Working directory in which to execute commands."""
    env: dict[str, str] = {}
    """Environment variables to set in the container."""
    forward_env: list[str] = []
    """Environment variables to forward to the container."""
    timeout: int = 30
    """Timeout for executing commands in the container."""
    executable: str = "enroot"
    """Path to the enroot executable."""
    start_args: list[str] = []
    """Additional arguments to pass to the `enroot start` command."""


class EnrootEnvironment(Environment):
    def __init__(
        self, *, config_class: type = EnrootEnvironmentConfig, logger: logging.Logger | None = None, **kwargs
    ):
        """This class executes bash commands in an Enroot container.
        See `EnrootEnvironmentConfig` for keyword arguments.
        """
        self.logger = logger or logging.getLogger("agent_rollout_service.environment")
        self.config = config_class(**kwargs)
        self.container_name: str | None = None
        self._setup_container()

    def get_template_vars(self) -> dict[str, Any]:
        return self.config.model_dump()

    def _setup_container(self):
        """Imports the enroot image and creates the container filesystem."""
        container_dir = os.environ["ENROOT_CACHE_PATH"]
        container_output_path = os.path.join(container_dir, f"{self.config.image}.sqsh".replace("/", "_"))
        
        if not os.path.exists(container_output_path):
            import_cmd = [self.config.executable, "import", "-o", container_output_path, self.config.image]
            self.logger.info(f"Importing image with command: {shlex.join(import_cmd)}")
            try:
                subprocess.run(
                    import_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Enroot import failed.\nStderr: {e.stderr}\nStdout: {e.stdout}")
                raise
            self.logger.info(f"Successfully imported image '{self.config.image}'")
        else:
            self.logger.info(f"Image already present '{self.config.image}'")

        self.container_name = f"agent-rollout-service-{uuid.uuid4().hex[:8]}"
        create_cmd = [
            self.config.executable,
            "create",
            "--name",
            self.container_name,
            container_output_path,
        ]
        self.logger.info(f"Creating container with command: {shlex.join(create_cmd)}")
        try:
            subprocess.run(
                create_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Enroot create failed.\nStderr: {e.stderr}\nStdout: {e.stdout}")
            raise
        self.logger.info(f"Created container '{self.container_name}'")

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a command in the Enroot container and return the result as a dict."""
        cwd = cwd or self.config.cwd
        assert self.container_name, "Container not created"

        cmd = [
            self.config.executable,
            "start",
            "--rw",
            *self.config.start_args,
        ]
        
        for key in self.config.forward_env:
            if (value := os.getenv(key)) is not None:
                cmd.extend(["--env", f"{key}={value}"])
        for key, value in self.config.env.items():
            cmd.extend(["--env", f"{key}={value}"])
        
        cmd.extend([self.container_name, "bash", "-lc", command])
        
        result = subprocess.run(
            cmd,
            text=True,
            timeout=timeout or self.config.timeout,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return {"output": result.stdout, "returncode": result.returncode}

    def cleanup(self):
        """Removes the Enroot container and its filesystem."""
        if getattr(self, "container_name", None) is not None:
            self.logger.info(f"Removing container {self.container_name}")
            cmd = f"{self.config.executable} remove --force {self.container_name} >/dev/null 2>&1 &"
            subprocess.Popen(cmd, shell=True)

    def __del__(self):
        """Cleanup container when object is destroyed."""
        self.cleanup()
