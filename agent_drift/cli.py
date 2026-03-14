"""CLI for agent-drift — Rich output with progress bars."""
from __future__ import annotations

import asyncio
import os
import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .core.models import AgentConfig, ProbeConfig, ValueDimension, ViolationSeverity
from .core.probe import ProbeEngine
from .core.reporter import generate_html_report, generate_text_summary
from .agents.llm_agent import build_agent_config
from .agents.openclaw_agent import build_openclaw_config

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """🎯 agent-drift — Stress-test AI agents for goal drift and system prompt violations."""
    pass


@cli.command()
@click.option("--system-prompt", "-s", help="System prompt to test")
@click.option("--system-prompt-file", "-f", help="File containing system prompt")
@click.option("--openclaw-workspace", "-w", help="Path to OpenClaw workspace")
@click.option("--model", "-m", default="claude-sonnet-4-20250514", help="Model to test")
@click.option("--provider", "-p", default="anthropic", help="Provider (anthropic/openai/groq/ollama)")
@click.option("--rounds", "-r", default=3, help="Number of probe rounds per scenario")
@click.option("--turns", "-t", default=10, help="Turns per round")
@click.option("--parallel", default=3, help="Parallel probes")
@click.option("--judge-model", default="claude-sonnet-4-20250514", help="Model for evaluation")
@click.option("--judge-provider", default="anthropic", help="Provider for judge model")
@click.option("--output", "-o", default="drift-report.html", help="Output report path")
@click.option("--dimensions", "-d", multiple=True, help="Dimensions to test (default: all)")
@click.option("--name", "-n", default="agent", help="Name for the agent being tested")
def probe(system_prompt, system_prompt_file, openclaw_workspace, model, provider,
          rounds, turns, parallel, judge_model, judge_provider, output, dimensions, name):
    """Run adversarial probes against an AI agent."""

    # Build agent config
    if openclaw_workspace:
        console.print(f"[bold blue]📂 Loading OpenClaw workspace:[/] {openclaw_workspace}")
        agent_config = build_openclaw_config(openclaw_workspace, model, provider)
    elif system_prompt_file:
        with open(system_prompt_file) as f:
            system_prompt = f.read()
        agent_config = build_agent_config(model, provider, system_prompt, name=name)
    elif system_prompt:
        agent_config = build_agent_config(model, provider, system_prompt, name=name)
    else:
        console.print("[red]Error:[/] Provide --system-prompt, --system-prompt-file, or --openclaw-workspace")
        sys.exit(1)

    # Build probe config
    dims = [ValueDimension(d) for d in dimensions] if dimensions else list(ValueDimension)
    probe_config = ProbeConfig(
        rounds=rounds,
        turns_per_round=turns,
        parallel=parallel,
        judge_model=judge_model,
        judge_provider=judge_provider,
        dimensions=dims,
    )

    # Show what we're doing
    console.print()
    console.print(Panel(
        f"[bold]Model:[/] {agent_config.model}\n"
        f"[bold]Provider:[/] {agent_config.provider}\n"
        f"[bold]Agent:[/] {agent_config.name}\n"
        f"[bold]Rounds:[/] {rounds} per scenario\n"
        f"[bold]Turns:[/] {turns} per round\n"
        f"[bold]Dimensions:[/] {', '.join(d.label for d in dims if d != ValueDimension.PERSISTENCE)}\n"
        f"[bold]Judge:[/] {judge_model}",
        title="🎯 Agent Drift Probe",
        border_style="blue",
    ))
    console.print()

    # Run probes
    engine = ProbeEngine(agent_config, probe_config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running probes...", total=None)

        def on_progress(completed, total, dim, result):
            progress.update(task, total=total, completed=completed,
                          description=f"[cyan]Probing {dim.label}... ({completed}/{total})")
            severity = result.severity
            color = {"green": "green", "amber": "yellow", "red": "red"}[severity.value]
            emoji = {"green": "🟢", "amber": "🟡", "red": "🔴"}[severity.value]
            progress.console.print(
                f"  {emoji} {dim.label} probe: max violation {result.max_violation_score:.1%} [{color}]{severity.value}[/]"
            )

        report = asyncio.run(engine.run_all(progress_callback=on_progress))

    # Generate report
    console.print()
    html_path = generate_html_report(report, output)
    text_summary = generate_text_summary(report)

    # Display results
    console.print(Panel(text_summary, title="📊 Results", border_style="bold"))
    console.print(f"\n[bold green]📄 Report saved to:[/] {html_path}")

    # Return report for programmatic use
    return report


@cli.command()
@click.argument("input_path", default="drift-results.json")
@click.option("--output", "-o", default="drift-report.html", help="Output HTML path")
def report(input_path, output):
    """Generate an HTML report from saved probe results."""
    console.print(f"[bold blue]Generating report from {input_path}...[/]")
    # TODO: implement loading from saved results
    console.print("[yellow]Not yet implemented — run 'drift probe' to generate a report directly.[/]")


def main():
    cli()


if __name__ == "__main__":
    main()
