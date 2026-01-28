#!/usr/bin/env python3
"""Example CLI with cli-analytics integration."""
import click
import time
import random
import cli_analytics

# Initialize analytics (in real CLI, use env var for API key)
cli_analytics.init(
    api_key="cli__yT9ZNlxYHpkNghlGWVv7mXbMQ7CmUaC9nuLyzYn3Qw",  # Your API key
    tool_name="mycli",
    tool_version="1.0.0",
    endpoint="https://cli-analytics-1.onrender.com"
)


def track(command: list, exit_code: int, duration_ms: int, flags: list = None):
    """Helper to track and show recommendation on failure."""
    cli_analytics.track_command(command, exit_code, duration_ms=duration_ms, flags=flags or [])

    if exit_code != 0:
        hint = cli_analytics.get_recommendation(command[-1], failed=True)
        if hint:
            click.echo(click.style(f"💡 Tip: {hint}", fg="yellow"))


@click.group()
def cli():
    """mycli - A sample CLI with analytics."""
    pass


@cli.command()
def init():
    """Initialize a new project."""
    click.echo("Initializing project...")
    start = time.time()
    time.sleep(0.5)  # Simulate work
    duration = int((time.time() - start) * 1000)

    click.echo(click.style("✓ Project initialized", fg="green"))
    track(["mycli", "init"], exit_code=0, duration_ms=duration)


@cli.command()
@click.option("--env", default="dev", help="Target environment")
def build(env):
    """Build the project."""
    click.echo(f"Building for {env}...")
    start = time.time()
    time.sleep(1)  # Simulate work
    duration = int((time.time() - start) * 1000)

    # Simulate occasional failure
    if random.random() < 0.3:
        click.echo(click.style("✗ Build failed: missing dependencies", fg="red"))
        track(["mycli", "build"], exit_code=1, duration_ms=duration, flags=["--env"])
        raise SystemExit(1)

    click.echo(click.style("✓ Build complete", fg="green"))
    track(["mycli", "build"], exit_code=0, duration_ms=duration, flags=["--env"])


@cli.command()
@click.option("--force", is_flag=True, help="Force deployment")
@click.option("--env", default="dev", help="Target environment")
def deploy(force, env):
    """Deploy the project."""
    # A/B test: try new deploy flow
    variant = cli_analytics.get_variant("new-deploy-flow")

    if variant == "variant_a":
        click.echo(f"[NEW FLOW] Deploying to {env}...")
    else:
        click.echo(f"Deploying to {env}...")

    start = time.time()
    time.sleep(1.5)  # Simulate work
    duration = int((time.time() - start) * 1000)

    flags = ["--env"]
    if force:
        flags.append("--force")

    # Simulate occasional failure
    if random.random() < 0.2:
        click.echo(click.style("✗ Deploy failed: connection timeout", fg="red"))
        track(["mycli", "deploy"], exit_code=1, duration_ms=duration, flags=flags)
        raise SystemExit(1)

    click.echo(click.style(f"✓ Deployed to {env}", fg="green"))
    track(["mycli", "deploy"], exit_code=0, duration_ms=duration, flags=flags)


@cli.command()
def test():
    """Run tests."""
    click.echo("Running tests...")
    start = time.time()
    time.sleep(0.8)
    duration = int((time.time() - start) * 1000)

    if random.random() < 0.25:
        click.echo(click.style("✗ 2 tests failed", fg="red"))
        track(["mycli", "test"], exit_code=1, duration_ms=duration)
        raise SystemExit(1)

    click.echo(click.style("✓ All tests passed", fg="green"))
    track(["mycli", "test"], exit_code=0, duration_ms=duration)


if __name__ == "__main__":
    cli()
