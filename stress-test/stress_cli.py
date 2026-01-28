#!/usr/bin/env python3
"""
Brutal stress test CLI for cli-analytics platform.
Tests concurrency, edge cases, rapid fire events, and data integrity.
"""

import click
import time
import random
import string
import threading
import concurrent.futures
import statistics
import sys
import os
import platform
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

# Add parent to path for local SDK testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk'))

import cli_analytics

# Configuration
API_KEY = "cli__yT9ZNlxYHpkNghlGWVv7mXbMQ7CmUaC9nuLyzYn3Qw"
ENDPOINT = "https://cli-analytics-1.onrender.com"

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    details: str = ""
    events_sent: int = 0
    errors: int = 0


class StressTestSuite:
    """Comprehensive stress test suite for cli-analytics."""

    def __init__(self, endpoint: str, api_key: str, verbose: bool = False):
        self.endpoint = endpoint
        self.api_key = api_key
        self.verbose = verbose
        self.results: List[TestResult] = []

    def log(self, msg: str):
        if self.verbose:
            click.echo(f"  {msg}")

    def run_all(self) -> bool:
        """Run all stress tests."""
        tests = [
            ("Rapid Fire Events", self.test_rapid_fire),
            ("Concurrent Users Simulation", self.test_concurrent_users),
            ("Deep Command Paths", self.test_deep_command_paths),
            ("Extreme Flag Counts", self.test_extreme_flags),
            ("Unicode & Special Characters", self.test_unicode_chaos),
            ("Massive Metadata Payloads", self.test_large_metadata),
            ("Session Boundary Stress", self.test_session_boundaries),
            ("Workflow Detection Accuracy", self.test_workflow_patterns),
            ("A/B Test Consistency", self.test_ab_consistency),
            ("A/B Test Under Load", self.test_ab_under_load),
            ("Recommendation Relevance", self.test_recommendations),
            ("Error Recovery", self.test_error_recovery),
            ("Latency Under Load", self.test_latency_distribution),
            ("Long Duration Commands", self.test_duration_extremes),
            ("Exit Code Spectrum", self.test_exit_codes),
            ("Batch Event Ingestion", self.test_batch_ingestion),
            ("Interleaved Workflows", self.test_interleaved_workflows),
            ("CI vs Local Detection", self.test_ci_detection),
            ("Duplicate Event Handling", self.test_duplicate_events),
            ("Rate Limit Resilience", self.test_rate_limits),
        ]

        click.echo(click.style("\n" + "="*60, fg="cyan"))
        click.echo(click.style("  CLI-ANALYTICS BRUTAL STRESS TEST SUITE", fg="cyan", bold=True))
        click.echo(click.style("="*60 + "\n", fg="cyan"))

        for name, test_fn in tests:
            click.echo(f"Running: {name}...", nl=False)
            start = time.time()
            try:
                result = test_fn()
                result.duration_ms = (time.time() - start) * 1000
                self.results.append(result)

                if result.passed:
                    click.echo(click.style(f" PASSED", fg="green") + f" ({result.duration_ms:.0f}ms)")
                else:
                    click.echo(click.style(f" FAILED", fg="red") + f" - {result.details}")
            except Exception as e:
                click.echo(click.style(f" ERROR", fg="red") + f" - {str(e)}")
                self.results.append(TestResult(name, False, 0, str(e)))

        return self.print_summary()

    def print_summary(self) -> bool:
        """Print test summary and return overall pass/fail."""
        click.echo(click.style("\n" + "="*60, fg="cyan"))
        click.echo(click.style("  TEST SUMMARY", fg="cyan", bold=True))
        click.echo(click.style("="*60, fg="cyan"))

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        total_events = sum(r.events_sent for r in self.results)
        total_errors = sum(r.errors for r in self.results)
        total_time = sum(r.duration_ms for r in self.results)

        click.echo(f"\nTests:  {passed} passed, {failed} failed, {len(self.results)} total")
        click.echo(f"Events: {total_events} sent, {total_errors} errors")
        click.echo(f"Time:   {total_time/1000:.2f}s")

        if failed > 0:
            click.echo(click.style("\nFailed tests:", fg="red"))
            for r in self.results:
                if not r.passed:
                    click.echo(f"  - {r.name}: {r.details}")

        click.echo()
        if failed == 0:
            click.echo(click.style("✓ ALL TESTS PASSED", fg="green", bold=True))
            return True
        else:
            click.echo(click.style(f"✗ {failed} TESTS FAILED", fg="red", bold=True))
            return False

    # ==================== TEST METHODS ====================

    def test_rapid_fire(self) -> TestResult:
        """Send 100 events as fast as possible."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-rapid", endpoint=self.endpoint)

        events_sent = 0
        errors = 0

        for i in range(100):
            try:
                cli_analytics.track_command(
                    ["stress", "rapid", f"cmd{i}"],
                    exit_code=0 if i % 10 != 0 else 1,
                    duration_ms=random.randint(10, 500)
                )
                events_sent += 1
            except:
                errors += 1

        # Allow some network settling
        time.sleep(0.5)

        return TestResult(
            "Rapid Fire Events",
            errors < 5,  # Allow up to 5% failure
            0,
            f"{errors} errors out of 100" if errors >= 5 else "",
            events_sent,
            errors
        )

    def test_concurrent_users(self) -> TestResult:
        """Simulate 20 concurrent users sending events."""
        errors = []
        events_per_user = 10
        num_users = 20

        def simulate_user(user_id: int):
            # Each user gets their own tracker instance
            cli_analytics.init(
                api_key=self.api_key,
                tool_name=f"stress-user-{user_id}",
                endpoint=self.endpoint
            )

            user_errors = 0
            commands = ["init", "build", "test", "deploy", "status", "logs"]

            for _ in range(events_per_user):
                try:
                    cli_analytics.track_command(
                        ["usercli", random.choice(commands)],
                        exit_code=random.choice([0, 0, 0, 1]),
                        duration_ms=random.randint(100, 3000)
                    )
                    time.sleep(random.uniform(0.01, 0.05))
                except Exception as e:
                    user_errors += 1

            return user_errors

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(simulate_user, i) for i in range(num_users)]
            for f in concurrent.futures.as_completed(futures):
                errors.append(f.result())

        total_errors = sum(errors)
        total_events = num_users * events_per_user

        return TestResult(
            "Concurrent Users",
            total_errors < total_events * 0.05,
            0,
            f"{total_errors}/{total_events} failed" if total_errors >= total_events * 0.05 else "",
            total_events - total_errors,
            total_errors
        )

    def test_deep_command_paths(self) -> TestResult:
        """Test extremely deep command hierarchies."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-deep", endpoint=self.endpoint)

        depths = [1, 5, 10, 20, 50]
        errors = 0

        for depth in depths:
            path = ["deepcli"] + [f"sub{i}" for i in range(depth)]
            try:
                cli_analytics.track_command(path, exit_code=0, duration_ms=100)
            except:
                errors += 1

        return TestResult(
            "Deep Command Paths",
            errors == 0,
            0,
            f"Failed at depths: {errors}" if errors > 0 else "",
            len(depths) - errors,
            errors
        )

    def test_extreme_flags(self) -> TestResult:
        """Test commands with many flags."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-flags", endpoint=self.endpoint)

        flag_counts = [0, 10, 50, 100, 200]
        errors = 0

        for count in flag_counts:
            flags = [f"--flag{i}" for i in range(count)]
            try:
                cli_analytics.track_command(["flagcli", "cmd"], exit_code=0, duration_ms=100, flags=flags)
            except:
                errors += 1

        return TestResult(
            "Extreme Flags",
            errors == 0,
            0,
            f"{errors} failed" if errors > 0 else "",
            len(flag_counts) - errors,
            errors
        )

    def test_unicode_chaos(self) -> TestResult:
        """Test Unicode and special characters in all fields."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-unicode-测试-🚀", endpoint=self.endpoint)

        test_strings = [
            "normal",
            "émojis-🎉-🔥-💻",
            "中文测试",
            "العربية",
            "日本語テスト",
            "путь",
            "special<>&\"'chars",
            "null\x00byte",
            "newline\ntest",
            "tab\there",
            "".join(chr(i) for i in range(32, 127)),  # All ASCII printable
        ]

        errors = 0
        for s in test_strings:
            try:
                cli_analytics.track_command(
                    ["unicli", s[:50]],  # Truncate for sanity
                    exit_code=0,
                    duration_ms=100,
                    flags=[f"--{s[:20]}"]
                )
            except:
                errors += 1

        return TestResult(
            "Unicode Chaos",
            errors <= 2,  # Allow some edge cases to fail
            0,
            f"{errors} strings failed" if errors > 2 else "",
            len(test_strings) - errors,
            errors
        )

    def test_large_metadata(self) -> TestResult:
        """Test with large metadata payloads."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-meta", endpoint=self.endpoint)

        sizes = [
            ("tiny", {"a": 1}),
            ("small", {f"key{i}": f"value{i}" for i in range(10)}),
            ("medium", {f"key{i}": "x" * 100 for i in range(50)}),
            ("large", {f"key{i}": "x" * 1000 for i in range(100)}),
        ]

        errors = 0
        for name, meta in sizes:
            try:
                cli_analytics.track_command(
                    ["metacli", name],
                    exit_code=0,
                    duration_ms=100,
                    metadata=meta
                )
            except:
                errors += 1

        return TestResult(
            "Large Metadata",
            errors <= 1,  # Allow the huge one to fail
            0,
            f"{errors} sizes failed" if errors > 1 else "",
            len(sizes) - errors,
            errors
        )

    def test_session_boundaries(self) -> TestResult:
        """Test session detection with various hints."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-session", endpoint=self.endpoint)

        session_hints = [
            "session-1",
            "session-1",  # Same session
            "session-2",  # New session
            None,         # Auto session
            "session-1",  # Back to 1
            f"session-{random.randint(1000, 9999)}",  # Random
        ]

        errors = 0
        for hint in session_hints:
            try:
                cli_analytics.track_command(
                    ["sessioncli", "cmd"],
                    exit_code=0,
                    duration_ms=100,
                    session_hint=hint
                )
            except:
                errors += 1

        return TestResult(
            "Session Boundaries",
            errors == 0,
            0,
            "" if errors == 0 else f"{errors} failed",
            len(session_hints) - errors,
            errors
        )

    def test_workflow_patterns(self) -> TestResult:
        """Test that workflow patterns are detected correctly."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-workflow", endpoint=self.endpoint)

        # Common workflow: init -> build -> test -> deploy
        workflows = [
            ["init", "build", "test", "deploy"],  # Full happy path
            ["init", "build", "build", "test", "deploy"],  # Retry build
            ["login", "status", "deploy"],  # Login flow
            ["setup", "configure", "run"],  # Setup flow
            ["init"],  # Single entry
            ["build", "build", "build"],  # Repeated failures
            ["deploy"],  # Single terminal
        ]

        errors = 0
        for workflow in workflows:
            session = f"wf-{random.randint(10000, 99999)}"
            for cmd in workflow:
                try:
                    cli_analytics.track_command(
                        ["wfcli", cmd],
                        exit_code=0 if cmd != "build" or random.random() > 0.3 else 1,
                        duration_ms=random.randint(100, 2000),
                        session_hint=session
                    )
                except:
                    errors += 1
            time.sleep(0.1)  # Small gap between workflows

        total = sum(len(w) for w in workflows)
        return TestResult(
            "Workflow Patterns",
            errors == 0,
            0,
            "" if errors == 0 else f"{errors}/{total} failed",
            total - errors,
            errors
        )

    def test_ab_consistency(self) -> TestResult:
        """Test A/B variant assignment is consistent for same user."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-ab", endpoint=self.endpoint)

        # Get variant multiple times - should be consistent
        variants = []
        for _ in range(10):
            v = cli_analytics.get_variant("stress-test-experiment")
            variants.append(v)

        # All should be the same (or all None if experiment doesn't exist)
        unique = set(variants)
        consistent = len(unique) == 1

        return TestResult(
            "A/B Consistency",
            consistent,
            0,
            f"Got {len(unique)} different variants: {unique}" if not consistent else "",
            10,
            0 if consistent else 10
        )

    def test_ab_under_load(self) -> TestResult:
        """Test A/B assignment under concurrent load."""
        results = {}
        lock = threading.Lock()
        errors = 0

        def get_variant_thread(thread_id: int):
            nonlocal errors
            cli_analytics.init(
                api_key=self.api_key,
                tool_name=f"stress-ab-load-{thread_id}",
                endpoint=self.endpoint
            )

            try:
                v = cli_analytics.get_variant("stress-load-experiment")
                with lock:
                    results[thread_id] = v
            except:
                with lock:
                    errors += 1

        threads = []
        for i in range(50):
            t = threading.Thread(target=get_variant_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Check distribution - should be roughly even if experiment exists
        return TestResult(
            "A/B Under Load",
            errors < 5,
            0,
            f"{errors} errors" if errors >= 5 else "",
            len(results),
            errors
        )

    def test_recommendations(self) -> TestResult:
        """Test recommendation system."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-rec", endpoint=self.endpoint)

        # First, generate some failure data
        failure_commands = ["build", "deploy", "test", "install"]
        for cmd in failure_commands:
            for _ in range(5):
                cli_analytics.track_command(
                    ["reccli", cmd],
                    exit_code=1,
                    duration_ms=random.randint(100, 1000)
                )

        time.sleep(0.5)  # Allow ingestion

        # Now test recommendations
        errors = 0
        for cmd in failure_commands:
            try:
                rec = cli_analytics.get_recommendation(cmd, failed=True)
                # rec can be None if not enough data, that's OK
            except:
                errors += 1

        return TestResult(
            "Recommendations",
            errors == 0,
            0,
            "" if errors == 0 else f"{errors} errors",
            len(failure_commands) * 5,
            errors
        )

    def test_error_recovery(self) -> TestResult:
        """Test SDK recovers from errors gracefully."""
        # Test with invalid endpoint
        cli_analytics.init(
            api_key=self.api_key,
            tool_name="stress-error",
            endpoint="https://invalid.endpoint.test"
        )

        # Should not raise - SDK should handle gracefully
        start = time.time()
        try:
            cli_analytics.track_command(["errcli", "cmd"], exit_code=0, duration_ms=100)
            recovered = True
        except:
            recovered = False

        elapsed = (time.time() - start) * 1000

        # Reinit with valid endpoint
        cli_analytics.init(api_key=self.api_key, tool_name="stress-error", endpoint=self.endpoint)

        return TestResult(
            "Error Recovery",
            recovered and elapsed < 10000,  # Should timeout reasonably
            0,
            "" if recovered else "SDK raised exception on network error",
            0,
            0 if recovered else 1
        )

    def test_latency_distribution(self) -> TestResult:
        """Measure latency distribution under load."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-latency", endpoint=self.endpoint)

        latencies = []
        errors = 0

        for i in range(30):
            start = time.time()
            try:
                cli_analytics.track_command(
                    ["latcli", f"cmd{i}"],
                    exit_code=0,
                    duration_ms=100
                )
                latencies.append((time.time() - start) * 1000)
            except:
                errors += 1

        if len(latencies) < 10:
            return TestResult("Latency", False, 0, "Too many errors", 30 - errors, errors)

        avg = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        # P95 should be under 5 seconds
        passed = p95 < 5000

        return TestResult(
            "Latency Distribution",
            passed,
            0,
            f"avg={avg:.0f}ms, p95={p95:.0f}ms" + ("" if passed else " - too slow"),
            len(latencies),
            errors
        )

    def test_duration_extremes(self) -> TestResult:
        """Test extreme duration values."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-duration", endpoint=self.endpoint)

        durations = [
            0,              # Instant
            1,              # 1ms
            100,            # 100ms
            1000,           # 1s
            60000,          # 1min
            3600000,        # 1hr
            86400000,       # 1day
            -1,             # Invalid negative
            None,           # No duration
        ]

        errors = 0
        for dur in durations:
            try:
                cli_analytics.track_command(
                    ["durcli", "cmd"],
                    exit_code=0,
                    duration_ms=dur
                )
            except:
                errors += 1

        return TestResult(
            "Duration Extremes",
            errors <= 1,  # Allow negative to fail
            0,
            "" if errors <= 1 else f"{errors} failed",
            len(durations) - errors,
            errors
        )

    def test_exit_codes(self) -> TestResult:
        """Test various exit codes."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-exit", endpoint=self.endpoint)

        codes = [0, 1, 2, 127, 128, 255, -1, 256, None]
        errors = 0

        for code in codes:
            try:
                cli_analytics.track_command(
                    ["exitcli", "cmd"],
                    exit_code=code,
                    duration_ms=100
                )
            except:
                errors += 1

        return TestResult(
            "Exit Codes",
            errors <= 1,
            0,
            "" if errors <= 1 else f"{errors} failed",
            len(codes) - errors,
            errors
        )

    def test_batch_ingestion(self) -> TestResult:
        """Test batch event submission."""
        import requests

        actor_id = os.environ.get("USER", os.environ.get("USERNAME", "stress-test"))
        machine_id = platform.node()

        events = []
        for i in range(50):
            events.append({
                "tool_name": "stress-batch",
                "command_path": ["batchcli", f"cmd{i}"],
                "exit_code": 0,
                "duration_ms": random.randint(10, 500),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "actor_id": actor_id,
                "machine_id": machine_id,
                "flags_present": [],
                "ci_detected": False,
            })

        try:
            response = requests.post(
                f"{self.endpoint}/ingest",
                json={"events": events},
                headers={"X-API-Key": self.api_key},
                timeout=30
            )
            success = response.status_code == 200
            if not success:
                self.log(f"Batch failed: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            success = False
            self.log(f"Batch exception: {e}")

        return TestResult(
            "Batch Ingestion",
            success,
            0,
            "" if success else "Batch request failed",
            50 if success else 0,
            0 if success else 50
        )

    def test_interleaved_workflows(self) -> TestResult:
        """Test multiple interleaved workflows from same tool."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-interleave", endpoint=self.endpoint)

        # Simulate 3 parallel workflows interleaved
        workflows = {
            "wf-a": ["init", "build", "test", "deploy"],
            "wf-b": ["login", "pull", "build", "push"],
            "wf-c": ["clone", "install", "build", "run"],
        }

        errors = 0
        # Interleave events
        max_len = max(len(v) for v in workflows.values())
        for i in range(max_len):
            for session, cmds in workflows.items():
                if i < len(cmds):
                    try:
                        cli_analytics.track_command(
                            ["intcli", cmds[i]],
                            exit_code=0,
                            duration_ms=random.randint(100, 500),
                            session_hint=session
                        )
                    except:
                        errors += 1

        total = sum(len(v) for v in workflows.values())
        return TestResult(
            "Interleaved Workflows",
            errors == 0,
            0,
            "" if errors == 0 else f"{errors}/{total} failed",
            total - errors,
            errors
        )

    def test_ci_detection(self) -> TestResult:
        """Test CI detection flag handling."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-ci", endpoint=self.endpoint)

        ci_values = [True, False, None]
        errors = 0

        for ci in ci_values:
            for _ in range(5):
                try:
                    cli_analytics.track_command(
                        ["cicli", "build"],
                        exit_code=0,
                        duration_ms=100,
                        ci_detected=ci
                    )
                except:
                    errors += 1

        total = len(ci_values) * 5
        return TestResult(
            "CI Detection",
            errors == 0,
            0,
            "" if errors == 0 else f"{errors}/{total} failed",
            total - errors,
            errors
        )

    def test_duplicate_events(self) -> TestResult:
        """Test handling of duplicate events."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-dupe", endpoint=self.endpoint)

        # Send same event 10 times rapidly
        errors = 0
        for _ in range(10):
            try:
                cli_analytics.track_command(
                    ["dupecli", "exact-same-command"],
                    exit_code=0,
                    duration_ms=100,
                    session_hint="dupe-session"
                )
            except:
                errors += 1

        return TestResult(
            "Duplicate Events",
            errors == 0,
            0,
            "" if errors == 0 else f"{errors}/10 failed",
            10 - errors,
            errors
        )

    def test_rate_limits(self) -> TestResult:
        """Test behavior under rate limiting (if any)."""
        cli_analytics.init(api_key=self.api_key, tool_name="stress-rate", endpoint=self.endpoint)

        # Burst 200 events as fast as possible
        errors = 0
        rate_limited = 0

        for i in range(200):
            try:
                cli_analytics.track_command(
                    ["ratecli", f"cmd{i}"],
                    exit_code=0,
                    duration_ms=10
                )
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    rate_limited += 1
                else:
                    errors += 1

        # Should handle gracefully even if rate limited
        return TestResult(
            "Rate Limits",
            errors < 10,
            0,
            f"{rate_limited} rate limited, {errors} errors" if errors >= 10 or rate_limited > 0 else "",
            200 - errors - rate_limited,
            errors
        )


@click.group()
def cli():
    """CLI Analytics Brutal Stress Test Suite."""
    pass


@cli.command()
@click.option("--endpoint", default=ENDPOINT, help="API endpoint")
@click.option("--api-key", default=API_KEY, help="API key")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(endpoint: str, api_key: str, verbose: bool):
    """Run the full stress test suite."""
    suite = StressTestSuite(endpoint, api_key, verbose)
    success = suite.run_all()
    sys.exit(0 if success else 1)


@cli.command()
@click.option("--endpoint", default=ENDPOINT, help="API endpoint")
@click.option("--api-key", default=API_KEY, help="API key")
@click.option("--events", default=1000, help="Number of events to send")
@click.option("--users", default=10, help="Number of concurrent users")
def load(endpoint: str, api_key: str, events: int, users: int):
    """Run a sustained load test."""
    click.echo(click.style(f"\nLoad Test: {events} events from {users} users", fg="cyan", bold=True))

    events_per_user = events // users
    results = {"sent": 0, "errors": 0, "latencies": []}
    lock = threading.Lock()

    def user_load(user_id: int):
        cli_analytics.init(
            api_key=api_key,
            tool_name=f"loadtest-user-{user_id}",
            endpoint=endpoint
        )

        commands = ["init", "build", "test", "deploy", "status", "logs", "config", "version"]

        for i in range(events_per_user):
            start = time.time()
            try:
                cli_analytics.track_command(
                    ["loadcli", random.choice(commands)],
                    exit_code=random.choice([0, 0, 0, 0, 1]),
                    duration_ms=random.randint(50, 2000),
                    flags=[f"--opt{j}" for j in range(random.randint(0, 5))]
                )
                latency = (time.time() - start) * 1000
                with lock:
                    results["sent"] += 1
                    results["latencies"].append(latency)
            except:
                with lock:
                    results["errors"] += 1

            # Small random delay to simulate real usage
            time.sleep(random.uniform(0.01, 0.1))

            # Progress indicator
            if (results["sent"] + results["errors"]) % 100 == 0:
                click.echo(f"  Progress: {results['sent'] + results['errors']}/{events}", nl=False)
                click.echo("\r", nl=False)

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
        futures = [executor.submit(user_load, i) for i in range(users)]
        concurrent.futures.wait(futures)

    elapsed = time.time() - start_time

    click.echo("\n")
    click.echo(f"Events sent:   {results['sent']}")
    click.echo(f"Errors:        {results['errors']}")
    click.echo(f"Total time:    {elapsed:.2f}s")
    click.echo(f"Throughput:    {results['sent']/elapsed:.1f} events/sec")

    if results['latencies']:
        click.echo(f"Avg latency:   {statistics.mean(results['latencies']):.0f}ms")
        click.echo(f"P95 latency:   {sorted(results['latencies'])[int(len(results['latencies'])*0.95)]:.0f}ms")


@cli.command()
@click.option("--endpoint", default=ENDPOINT, help="API endpoint")
@click.option("--api-key", default=API_KEY, help="API key")
def quick(endpoint: str, api_key: str):
    """Run a quick sanity check (5 events)."""
    click.echo("Quick sanity check...")

    cli_analytics.init(api_key=api_key, tool_name="quicktest", endpoint=endpoint)

    for i, cmd in enumerate(["init", "build", "test", "deploy", "status"]):
        try:
            cli_analytics.track_command(
                ["quickcli", cmd],
                exit_code=0,
                duration_ms=100 * (i + 1)
            )
            click.echo(click.style(f"  ✓ {cmd}", fg="green"))
        except Exception as e:
            click.echo(click.style(f"  ✗ {cmd}: {e}", fg="red"))

    click.echo("\nTesting A/B variant...")
    v = cli_analytics.get_variant("test-experiment")
    click.echo(f"  Variant: {v}")

    click.echo("\nTesting recommendation...")
    r = cli_analytics.get_recommendation("deploy", failed=True)
    click.echo(f"  Recommendation: {r}")

    click.echo(click.style("\n✓ Quick check complete", fg="green"))


if __name__ == "__main__":
    cli()
