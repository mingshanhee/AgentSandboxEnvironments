import argparse
import uvicorn
import json
import logging
from runners.local import LocalRunner
from runners.slurm import SlurmRunner
from api import create_app

def main():
    parser = argparse.ArgumentParser(description="Agent Rollout Service CLI")
    parser.add_argument("--runner", choices=["local", "slurm"], required=True, help="Runner type")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the API on")
    parser.add_argument("--max-resources", type=str, default='{"instances": 10}', help="JSON string for max resources")
    parser.add_argument("--environments", type=str, default=None, help="Path to environments JSON file")
    
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    try:
        max_resources = json.loads(args.max_resources)
    except json.JSONDecodeError:
        print("Error: Invalid JSON for --max-resources")
        return

    environments = {}
    if args.environments:
        try:
            with open(args.environments, 'r') as f:
                environments = json.load(f)
        except Exception as e:
            print(f"Error loading environments file: {e}")
            return

    if args.runner == "local":
        runner = LocalRunner(max_resources)
    elif args.runner == "slurm":
        runner = SlurmRunner(max_resources)
    else:
        # Should be caught by argparse choices
        print("Invalid runner type")
        return

    app = create_app(runner, environments=environments)
    
    print(f"Starting {args.runner} runner API on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port)

if __name__ == "__main__":
    main()
