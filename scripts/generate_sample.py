#!/usr/bin/env python3
"""Generate sample CLI events for testing."""
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Sample tool configurations
TOOLS = [
    {"name": "terraform", "version": "1.7.0", "commands": ["init", "plan", "apply", "destroy", "validate"]},
    {"name": "kubectl", "version": "1.29.0", "commands": ["apply", "get", "delete", "rollout", "logs", "describe"]},
    {"name": "docker", "version": "24.0.7", "commands": ["build", "push", "pull", "run", "compose"]},
    {"name": "npm", "version": "10.2.0", "commands": ["install", "build", "test", "publish", "run"]},
    {"name": "git", "version": "2.43.0", "commands": ["clone", "commit", "push", "pull", "merge", "checkout"]},
]

# Typical workflow sequences
WORKFLOWS = {
    "terraform_deploy": [
        (["terraform", "init"], 0),
        (["terraform", "validate"], 0),
        (["terraform", "plan"], 0),
        (["terraform", "apply"], None),  # None = variable exit code
    ],
    "docker_build_push": [
        (["docker", "build"], None),
        (["docker", "push"], None),
    ],
    "npm_test_publish": [
        (["npm", "install"], 0),
        (["npm", "test"], None),
        (["npm", "build"], None),
        (["npm", "publish"], None),
    ],
    "k8s_deploy": [
        (["kubectl", "apply"], None),
        (["kubectl", "rollout"], None),
    ],
}

# Common flags by tool
FLAGS = {
    "terraform": ["--auto-approve", "-var-file", "--target", "-parallelism"],
    "kubectl": ["-n", "--namespace", "-f", "--dry-run", "-o"],
    "docker": ["-t", "--tag", "-f", "--file", "--no-cache", "--platform"],
    "npm": ["--save-dev", "--production", "--legacy-peer-deps"],
    "git": ["-m", "--amend", "--force", "-b", "--no-verify"],
}


def generate_actor_id() -> str:
    """Generate a random actor ID."""
    return f"user_{uuid.uuid4().hex[:8]}"


def generate_machine_id() -> str:
    """Generate a random machine ID."""
    return f"machine_{uuid.uuid4().hex[:8]}"


def generate_workflow_events(
    workflow_type: str,
    actor_id: str,
    machine_id: str,
    base_time: datetime,
    ci_detected: bool = False,
    session_hint: Optional[str] = None,
    introduce_failure: bool = False,
    failure_step: Optional[int] = None,
) -> list:
    """Generate events for a complete workflow."""
    events = []
    workflow = WORKFLOWS[workflow_type]
    current_time = base_time

    for i, (command_path, expected_exit) in enumerate(workflow):
        # Determine exit code
        if introduce_failure and failure_step is not None and i == failure_step:
            exit_code = 1
        elif expected_exit is None:
            exit_code = 0 if random.random() > 0.15 else 1  # 15% natural failure rate
        else:
            exit_code = expected_exit

        # Get tool info
        tool_name = command_path[0]
        tool = next(t for t in TOOLS if t["name"] == tool_name)

        # Random duration between 500ms and 30s
        duration_ms = random.randint(500, 30000)

        # Random flags
        tool_flags = FLAGS.get(tool_name, [])
        flags_present = random.sample(tool_flags, k=min(random.randint(0, 3), len(tool_flags)))

        event = {
            "timestamp": current_time.isoformat(),
            "tool_name": tool_name,
            "tool_version": tool["version"],
            "command_path": command_path,
            "flags_present": flags_present,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "error_type": "ExitError" if exit_code != 0 else None,
            "actor_id": actor_id,
            "machine_id": machine_id,
            "session_hint": session_hint,
            "ci_detected": ci_detected,
        }
        events.append(event)

        # Advance time by duration + some think time
        current_time += timedelta(milliseconds=duration_ms + random.randint(1000, 10000))

        # Stop if command failed
        if exit_code != 0:
            break

    return events


def generate_sample_data(output_path: str = "events.jsonl"):
    """Generate a sample dataset of CLI events."""
    all_events = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=24)

    # Generate human sessions (multiple users, varying patterns)
    print("Generating human sessions...")
    for user_num in range(5):
        actor_id = generate_actor_id()
        machine_id = generate_machine_id()
        session_time = base_time + timedelta(hours=user_num * 2)

        # Each user does 2-4 workflows per session
        for workflow_num in range(random.randint(2, 4)):
            workflow_type = random.choice(list(WORKFLOWS.keys()))

            # Some workflows fail
            introduce_failure = random.random() < 0.25
            failure_step = random.randint(1, len(WORKFLOWS[workflow_type]) - 1) if introduce_failure else None

            events = generate_workflow_events(
                workflow_type=workflow_type,
                actor_id=actor_id,
                machine_id=machine_id,
                base_time=session_time,
                ci_detected=False,
                introduce_failure=introduce_failure,
                failure_step=failure_step,
            )
            all_events.extend(events)

            # Time gap between workflows
            if events:
                last_event_time = datetime.fromisoformat(events[-1]["timestamp"])
                session_time = last_event_time + timedelta(minutes=random.randint(5, 20))

    # Generate CI sessions (consistent patterns, higher volume)
    print("Generating CI sessions...")
    for ci_run in range(10):
        actor_id = "ci-runner"
        machine_id = f"ci-agent-{ci_run % 3}"
        session_hint = f"ci-run-{uuid.uuid4().hex[:8]}"
        session_time = base_time + timedelta(hours=ci_run)

        # CI typically runs the same workflow
        workflow_type = random.choice(["terraform_deploy", "npm_test_publish", "docker_build_push"])

        # CI has lower failure rate
        introduce_failure = random.random() < 0.10
        failure_step = random.randint(1, len(WORKFLOWS[workflow_type]) - 1) if introduce_failure else None

        events = generate_workflow_events(
            workflow_type=workflow_type,
            actor_id=actor_id,
            machine_id=machine_id,
            base_time=session_time,
            ci_detected=True,
            session_hint=session_hint,
            introduce_failure=introduce_failure,
            failure_step=failure_step,
        )
        all_events.extend(events)

    # Generate some abandoned sessions (user starts but doesn't finish)
    print("Generating abandoned sessions...")
    for abandon_num in range(3):
        actor_id = generate_actor_id()
        machine_id = generate_machine_id()
        session_time = base_time + timedelta(hours=abandon_num * 3 + 1)

        workflow_type = random.choice(list(WORKFLOWS.keys()))
        workflow = WORKFLOWS[workflow_type]

        # Only complete first 1-2 commands
        partial_workflow = {workflow_type: workflow[:random.randint(1, 2)]}
        original = WORKFLOWS[workflow_type]
        WORKFLOWS[workflow_type] = partial_workflow[workflow_type]

        events = generate_workflow_events(
            workflow_type=workflow_type,
            actor_id=actor_id,
            machine_id=machine_id,
            base_time=session_time,
            ci_detected=False,
        )
        all_events.extend(events)

        # Restore workflow
        WORKFLOWS[workflow_type] = original

    # Generate retry scenarios (user retries after failure)
    print("Generating retry scenarios...")
    for retry_num in range(3):
        actor_id = generate_actor_id()
        machine_id = generate_machine_id()
        session_time = base_time + timedelta(hours=retry_num * 4 + 2)

        workflow_type = random.choice(list(WORKFLOWS.keys()))

        # First attempt fails
        events = generate_workflow_events(
            workflow_type=workflow_type,
            actor_id=actor_id,
            machine_id=machine_id,
            base_time=session_time,
            ci_detected=False,
            introduce_failure=True,
            failure_step=len(WORKFLOWS[workflow_type]) - 1,
        )
        all_events.extend(events)

        # Retry after some time
        if events:
            retry_time = datetime.fromisoformat(events[-1]["timestamp"]) + timedelta(minutes=random.randint(2, 10))

            events = generate_workflow_events(
                workflow_type=workflow_type,
                actor_id=actor_id,
                machine_id=machine_id,
                base_time=retry_time,
                ci_detected=False,
                introduce_failure=False,  # Retry succeeds
            )
            all_events.extend(events)

    # Sort by timestamp
    all_events.sort(key=lambda e: e["timestamp"])

    # Write to file
    output_file = Path(output_path)
    with output_file.open("w") as f:
        for event in all_events:
            f.write(json.dumps(event) + "\n")

    print(f"\nGenerated {len(all_events)} events")
    print(f"Written to: {output_file.absolute()}")

    # Summary
    ci_events = sum(1 for e in all_events if e["ci_detected"])
    human_events = len(all_events) - ci_events
    print(f"  - Human events: {human_events}")
    print(f"  - CI events: {ci_events}")


if __name__ == "__main__":
    generate_sample_data()
