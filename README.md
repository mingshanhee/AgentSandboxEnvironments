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
| `--port` | Port to run the HTTP API on. | `8000` |
| `--max-resources` | JSON string defining maximum available resources. | `{"instances": 10}` |
| `--environments` | Path to a JSON file containing pre-defined environment configurations. | `None` |

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

- `POST /start_instance`: Start a new environment instance.
- `POST /execute_command`: Run a shell command in an instance.
- `POST /close_instance`: Stop and clean up an instance.
- `GET /get_available_resources`: Check current resource usage.
