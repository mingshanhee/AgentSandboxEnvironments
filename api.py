from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from runners.base import BaseRunner


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

    return app
