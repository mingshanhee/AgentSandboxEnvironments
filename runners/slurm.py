from typing import Any, Dict
import subprocess
import logging
from runners.base import BaseRunner

logger = logging.getLogger(__name__)

class SlurmRunner(BaseRunner):
    """Runner for Slurm execution."""

    def __init__(self, max_resources: Dict[str, Any]):
        super().__init__(max_resources)

    def start_instance(self, container_name: str, run_id: str, environment_config: Dict[str, Any]) -> str:
        """Starts a Slurm job instance."""
        # Check resources (simplified: assume 1 unit of 'jobs' unless specified)
        needed_resources = environment_config.get("resources", {"instances": 1})
        if not self._check_resources(needed_resources):
            raise RuntimeError(f"Not enough resources. Available: {self.get_available_resources()}")

        # Extract sbatch options from config
        sbatch_args = environment_config.get("sbatch_args", [])
        
        # We start a sleeper job so we can execute commands in it
        # Construct sbatch command
        cmd = ["sbatch", "--parsable"] + sbatch_args
        
        # Script to run (sleep forever so we can connect)
        script = "#!/bin/bash\nsleep infinity"
        
        try:
            result = subprocess.run(
                cmd,
                input=script,
                capture_output=True,
                text=True,
                check=True
            )
            job_id = result.stdout.strip()
            # If job_id has ; (cluster name), take first part
            if ";" in job_id:
                job_id = job_id.split(";")[0]

            self.running_instances[run_id] = {
                "container_name": container_name,
                "job_id": job_id,
                "resources": needed_resources
            }
            self._allocate_resources(needed_resources)
            logger.info(f"Started Slurm job {job_id} for container {container_name}, run {run_id}")
            return run_id
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to submit Slurm job for container {container_name}, run {run_id}: {e.stderr}")
            raise

    def execute_command(self, run_id: str, cmd: str) -> Dict[str, Any]:
        """Executes a command in the Slurm job."""
        if run_id not in self.running_instances:
            raise KeyError(f"Run ID {run_id} not found.")

        job_id = self.running_instances[run_id]["job_id"]
        
        # Use srun to execute within the allocation
        # --overlap allows sharing the allocation
        full_cmd = ["srun", "--jobid", job_id, "--overlap", "bash", "-c", cmd]
        
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                check=False # Don't raise, return returncode
            )
            return {"output": result.stdout + result.stderr, "returncode": result.returncode}
        except Exception as e:
            logger.error(f"Failed to execute command in job {job_id} for run {run_id}: {e}")
            raise

    def close_instance(self, run_id: str) -> None:
        """Closes the Slurm instance (cancels job)."""
        if run_id not in self.running_instances:
            return

        job_id = self.running_instances[run_id]["job_id"]
        resources = self.running_instances[run_id]["resources"]
        
        try:
            subprocess.run(["scancel", job_id], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to cancel job {job_id} for run {run_id}: {e}")
            # We still remove it from our list as it's likely gone or we lost control
        
        self._release_resources(resources)
        del self.running_instances[run_id]
