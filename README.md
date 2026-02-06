# Agent Rollout Service

The Agent Rollout Service is a service designed to manage containerized environments and execute commands within them, supporting both local and HPC (Slurm) execution contexts. It exposes a REST API for clients to interact with these resources.

## Folder Structure

- **`runners/`**: Contains the logic for resource management and execution.
    - `BaseRunner`: Abstract base class handling resource accounting.
    - `LocalRunner`: Executes environments on the local machine.
    - `SlurmRunner`: Submits jobs to a Slurm cluster.
- **`environments/`**: Defines various execution environments.
    - `Environment`: Base class for all environments.
    - Implementations include `docker`, `singularity`, `enroot`, and `local` execution.
    - `extra/`: Contains additional experimental environments (e.g., `bubblewrap`).
- **`models/`**: (Optional) wrappers for LLM interactions if the service needs to perform model inference or cost tracking internally.
    - Includes support for `litellm`, `anthropic`, `openrouter`, etc.
    - Removed external dependencies to make it standalone.
- **`tests/`**: Contains `pytest` test suites for runners and the API.
- **`api.py`**: FastAPI application exposing endpoints like `/start_instance`, `/execute_command`, and `/get_available_resources`.
- **`cli.py`**: Command-line interface entry point.

## Installation

Install the package (editable mode recommended for development):

```bash
pip install -e .
```

This installs the `arservice` command.

## Usage

Start the service using the `arservice` CLI.

### Command Syntax

```bash
arservice --runner <local|slurm> [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--runner` | **Required**. Type of runner to use: `local` or `slurm`. | - |
| `--port` | Port to run the HTTP API on. | `8008` |
| `--max-resources` | JSON string defining maximum available resources (e.g., `{"instances": 10, "cpus": 40}`). Only keys defined here are strictly enforced; others are allowed but ignored for accounting. | `{"instances": 10}` |
| `--environments` | Path to a JSON file containing pre-defined environment configurations. | `None` |

### Resource Management

The service performs admission control based on the resources defined in `--max-resources`. 
- **Enforced Resources**: If a request (via `environment_config.resources`) asks for a resource key that is present in the server's `--max-resources`, the service ensures there is enough remaining capacity.
- **Untracked Resources**: Resource types (like `cpus`, `memory`, or `gpus`) can be included in request payloads even if the server is not configured to track them. These will be passed through to the underlying environment (e.g., Docker) but will not be used for admission control or resource accounting in the service itself.

Example starting with CPU and memory tracking:
```bash
arservice --runner local --max-resources '{"instances": 10, "cpus": 32, "memory_gb": 128}'
```

### Examples

**Start a Local Runner:**
Allows up to 5 concurrent instances.

```bash
arservice --runner local --max-resources '{"instances": 5}'
```

**Start a Slurm Runner:**
Allows up to 20 concurrent jobs.

```bash
arservice --runner slurm --max-resources '{"jobs": 20}'
```

## API Endpoints

Once running, the API is available at `http://localhost:<PORT>`.

### 1. `POST /start_instance`
Starts a new instance of an environment.

**Request Body:**
```json
{
  "container_name": "string",
  "run_id": "string",
  "environment_config": {}
}
```

<details>
<summary><b>Sample Request (curl)</b></summary>

```bash
curl -X POST http://localhost:8008/start_instance \
  -H "Content-Type: application/json" \
  -d '{
    "container_name": "xingyaoww/sweb.eval.x86_64.python_s_mypy-5617:latest",
    "run_id": "eval-run-001",
    "environment_config": {
      "container_type": "docker",
      "image": "xingyaoww/sweb.eval.x86_64.python_s_mypy-5617:latest"
    }
  }'
```
</details>

<details>
<summary><b>Sample Response</b></summary>

```json
{
  "status": "success",
  "instance_id": "eval-run-001"
}
```
</details>

### 2. `POST /execute_command`
Runs a shell command in a running instance.

**Request Body:**
```json
{
  "run_id": "string",
  "cmd": "string"
}
```

<details>
<summary><b>Sample Request (curl)</b></summary>

```bash
curl -X POST http://localhost:8008/execute_command \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "eval-run-001",
    "cmd": "ls -R"
  }'
```
</details>

<details>
<summary><b>Sample Response</b></summary>

```json
{
  "status": "success",
  "result": {
    "output": "total 4\n-rw-r--r-- 1 root root 2672 Jan 22 17:28 README.md\n...",
    "returncode": 0
  }
}
```
</details>

### 3. `POST /close_instance`
Stops and cleans up an instance.

**Request Body:**
```json
{
  "run_id": "string"
}
```

<details>
<summary><b>Sample Request (curl)</b></summary>

```bash
curl -X POST http://localhost:8008/close_instance \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "eval-run-001"
  }'
```
</details>

<details>
<summary><b>Sample Response</b></summary>

```json
{
  "status": "success"
}
```
</details>

### 4. `GET /get_available_resources`
Check current resource usage and availability.

<details>
<summary><b>Sample Request (curl)</b></summary>

```bash
curl http://localhost:8008/get_available_resources
```
</details>

<details>
<summary><b>Sample Response</b></summary>

```json
{
  "instances": 5
}
```
</details>

## Monitoring

### Polling Stats

The service includes a `poll.py` utility for monitoring active instances and resource usage in real-time.

```bash
python poll.py --url http://localhost:8008 --list
```

**Options:**
- `--url`: Base URL of the service.
- `--list`: Show a detailed table of active instances (run ID, container, start time).
- `--interval`: Refresh rate in seconds (default: 1.0).
- `--raw`: Print the raw JSON response from the `/stats` endpoint.
