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
    run_id: str
    container_image: str
    container_type: str
    timeout: int = 300
    resources: Dict[str, Any] = {"instances": 1}

class ExecuteCommandRequest(BaseModel):
    run_id: str
    cmd: str

class CloseInstanceRequest(BaseModel):
    run_id: str


def create_app(runner: BaseRunner) -> FastAPI:
    app = FastAPI()
    started_at = time.time()

    @app.post("/start_instance")
    def start_instance(request: StartInstanceRequest):
        try:
            # Convert request to dictionary
            request_params = request.model_dump()
            
            instance_id = runner.start_instance(request_params)
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
                instance_container = instance_data.get("container_image", "")
                if container_name not in instance_container:
                    continue
            
            container = instance_data.get("container_image", "unknown")
            container_counts[container] = container_counts.get(container, 0) + 1
            instances.append({
                "run_id": rid,
                "container_image": container,
                "created_at": instance_data.get("created_at"),
                "updated_at": instance_data.get("updated_at"),
                "num_cmd": instance_data.get("num_cmd"),
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
