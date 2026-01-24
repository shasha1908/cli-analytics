#!/usr/bin/env python3
"""Post events from a JSONL file to the /ingest endpoint."""
import argparse
import json
import sys
from pathlib import Path

import httpx


def post_events(
    events_file: str,
    base_url: str = "http://localhost:8000",
    batch_size: int = 100,
):
    """Post events to the /ingest endpoint."""
    events_path = Path(events_file)

    if not events_path.exists():
        print(f"Error: File not found: {events_path}")
        sys.exit(1)

    # Read events
    events = []
    with events_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    print(f"Loaded {len(events)} events from {events_path}")

    # Post in batches
    total_accepted = 0
    total_rejected = 0

    client = httpx.Client(base_url=base_url, timeout=30.0)

    try:
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]

            if len(batch) == 1:
                # Single event
                response = client.post("/ingest", json=batch[0])
            else:
                # Batch
                response = client.post("/ingest", json={"events": batch})

            if response.status_code == 200:
                result = response.json()
                total_accepted += result["accepted"]
                total_rejected += result["rejected"]
                print(f"  Batch {i // batch_size + 1}: {result['accepted']} accepted, {result['rejected']} rejected")
            else:
                print(f"  Batch {i // batch_size + 1}: Error {response.status_code} - {response.text}")
                total_rejected += len(batch)
    finally:
        client.close()

    print(f"\nTotal: {total_accepted} accepted, {total_rejected} rejected")

    return total_accepted, total_rejected


def run_inference(base_url: str = "http://localhost:8000"):
    """Trigger inference."""
    print("\nRunning inference...")
    client = httpx.Client(base_url=base_url, timeout=60.0)

    try:
        response = client.post("/infer")
        if response.status_code == 200:
            result = response.json()
            print(f"  Events processed: {result['events_processed']}")
            print(f"  Sessions created: {result['sessions_created']}")
            print(f"  Workflows created: {result['workflows_created']}")
        else:
            print(f"  Error: {response.status_code} - {response.text}")
    finally:
        client.close()


def get_summary(base_url: str = "http://localhost:8000"):
    """Fetch and display summary report."""
    print("\nFetching summary report...")
    client = httpx.Client(base_url=base_url, timeout=30.0)

    try:
        response = client.get("/reports/summary")
        if response.status_code == 200:
            result = response.json()
            print(f"\n{'='*60}")
            print("SUMMARY REPORT")
            print(f"{'='*60}")
            print(f"Total Events:    {result['total_events']}")
            print(f"Total Sessions:  {result['total_sessions']}")
            print(f"Total Workflows: {result['total_workflows']}")

            print(f"\n{'='*60}")
            print("TOP WORKFLOWS")
            print(f"{'='*60}")
            for wf in result["top_workflows"]:
                print(f"\n  {wf['workflow_name']}")
                print(f"    Runs: {wf['total_runs']} | Success: {wf['success_rate']}%")
                print(f"    Success: {wf['success_count']} | Failed: {wf['failed_count']} | Abandoned: {wf['abandoned_count']}")
                if wf["median_duration_ms"]:
                    print(f"    Median Duration: {wf['median_duration_ms']}ms")

            if result["failure_hot_paths"]:
                print(f"\n{'='*60}")
                print("FAILURE HOT PATHS")
                print(f"{'='*60}")
                for hp in result["failure_hot_paths"][:5]:
                    print(f"\n  [{hp['failure_count']} failures] {hp['workflow_name']}")
                    print(f"    {hp['command_fingerprint']}")
        else:
            print(f"  Error: {response.status_code} - {response.text}")
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Post CLI events and analyze results")
    parser.add_argument("events_file", nargs="?", default="events.jsonl", help="Path to events JSONL file")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for posting events")
    parser.add_argument("--infer", action="store_true", help="Run inference after posting")
    parser.add_argument("--summary", action="store_true", help="Show summary report after inference")
    parser.add_argument("--all", action="store_true", help="Post, infer, and show summary")

    args = parser.parse_args()

    if args.all:
        args.infer = True
        args.summary = True

    # Post events
    post_events(args.events_file, args.url, args.batch_size)

    # Run inference if requested
    if args.infer:
        run_inference(args.url)

    # Show summary if requested
    if args.summary:
        get_summary(args.url)


if __name__ == "__main__":
    main()
