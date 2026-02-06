#!/usr/bin/env python3
"""
Poll the AgentRolloutService for statistics.
Usage:
    python poll.py --url http://127.0.0.1:8008 --list
"""
import argparse
import datetime as dt
import json
import sys
import time
from typing import Any

import requests


def _fmt_ts(ts: float | None) -> str:
    if ts is None:
        return "never"
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat()


def _print_summary(stats: dict[str, Any]) -> None:
    print(f"Server time: {_fmt_ts(stats.get('server_time'))}")
    print(f"Uptime: {stats.get('uptime_s', 0):.1f}s")
    print(f"Active instances: {stats.get('active_instances', 0)}/{stats.get('total_instances', 0)}")
    
    resources = stats.get("available_resources", {})
    max_res = stats.get("max_resources", {})
    alloc_res = stats.get("allocated_resources", {})
    
    print(f"Resources (inst): {alloc_res.get('instances', 0)}/{max_res.get('instances', 0)} allocated, {resources.get('instances', 0)} available")

    container_counts = stats.get("container_counts", {}) or {}
    if container_counts:
        print("Containers:")
        for container, count in sorted(container_counts.items()):
            print(f"  {container}: {count}")


def _print_instances(stats: dict[str, Any]) -> None:
    instances = list(stats.get("instances", []) or [])
    if not instances:
        print("No active instances.")
        return

    print("Active instances:")
    print("  run_id                               container            created_at")
    for item in instances:
        run_id = str(item.get("run_id", ""))
        container = str(item.get("container_name", ""))
        created_at = _fmt_ts(item.get("created_at"))
        print(f"  {run_id:36}  {container:18}  {created_at}")


def fetch_and_display(url: str, list_instances: bool, raw: bool) -> None:
    try:
        base = url.rstrip("/")
        resp = requests.get(f"{base}/stats", timeout=5)
        resp.raise_for_status()
        stats = resp.json()
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return

    if raw:
        print(json.dumps(stats, indent=2))
        return

    _print_summary(stats)
    if list_instances:
        _print_instances(stats)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query AgentRolloutService stats")
    parser.add_argument("--url", default="http://127.0.0.1:8008", help="Service base URL, e.g. http://127.0.0.1:8008")
    parser.add_argument("--list", action="store_true", help="List active instances")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON response")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds (default: 1.0)")
    args = parser.parse_args()

    try:
        while True:
            # Clear screen (ANSI escape code)
            sys.stdout.write("\033[H\033[J")
            sys.stdout.flush()
            
            fetch_and_display(args.url, args.list, args.raw)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C without showing traceback
        sys.exit(0)


if __name__ == "__main__":
    main()
