import time
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from runners.base import BaseRunner


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /stats") == -1


class StartInstanceRequest(BaseModel):
    container_name: str
    run_id: str
    environment_config: Dict[str, Any] = {}

class ExecuteCommandRequest(BaseModel):
    run_id: str
    cmd: str

class CloseInstanceRequest(BaseModel):
    run_id: str


def create_app(runner: BaseRunner, environments: Dict[str, Dict[str, Any]] = {}) -> FastAPI:
    app = FastAPI()
    started_at = time.time()

    @app.post("/start_instance")
    def start_instance(request: StartInstanceRequest):
        try:
            # Check if container_name maps to a pre-defined environment
            if request.container_name in environments:
                env_config = environments[request.container_name]
                # If the config is just a string, assume it's a docker image name
                if isinstance(env_config, str):
                    env_config = {"container_type": "docker", "image": env_config}
                
                # If the request provides overrides or additional config, merge them
                if request.environment_config:
                     env_config = {**env_config, **request.environment_config}
            else:
                # If not in environments, rely fully on request payload (backward compatibility or flexible usage)
                env_config = request.environment_config
            
            if not env_config:
                 raise HTTPException(status_code=400, detail="Environment configuration not found for instance")

            instance_id = runner.start_instance(request.container_name, request.run_id, env_config)
            return {"status": "success", "instance_id": instance_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/execute_command")
    def execute_command(request: ExecuteCommandRequest):
        try:
            result = runner.execute_command(request.run_id, request.cmd)
            return {"status": "success", "result": result}
        except KeyError:
            raise HTTPException(status_code=404, detail="Instance not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/get_available_resources")
    def get_available_resources():
        return runner.get_available_resources()

    @app.post("/close_instance")
    def close_instance(request: CloseInstanceRequest):
        try:
            runner.close_instance(request.run_id)
            return {"status": "success"}
        except KeyError:
             raise HTTPException(status_code=404, detail="Instance not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/stats")
    def stats(
        run_id: Optional[str] = Query(None, description="Filter by run ID"),
        container_name: Optional[str] = Query(None, description="Filter by container name"),
    ):
        """
        Get server statistics with optional filtering.
        
        - **run_id**: Filter instances by run ID (partial match supported)
        - **container_name**: Filter instances by container name (partial match supported)
        """
        instances: List[Dict[str, Any]] = []
        container_counts: Dict[str, int] = {}
        
        for rid, instance_data in runner.running_instances.items():
            # Apply filters
            if run_id and run_id not in rid:
                continue
            if container_name:
                instance_container = instance_data.get("container_name", "")
                if container_name not in instance_container:
                    continue
            
            container = instance_data.get("container_name", "unknown")
            container_counts[container] = container_counts.get(container, 0) + 1
            instances.append({
                "run_id": rid,
                "container_name": container,
                "created_at": instance_data.get("created_at"),
                "environment_config": instance_data.get("environment_config", {}),
            })
        
        return {
            "server_time": time.time(),
            "uptime_s": time.time() - started_at,
            "active_instances": len(instances),
            "total_instances": len(runner.running_instances),
            "max_resources": runner.max_resources,
            "allocated_resources": runner.allocated_resources,
            "available_resources": runner.get_available_resources(),
            "container_counts": container_counts,
            "instances": instances,
        }

    return app
