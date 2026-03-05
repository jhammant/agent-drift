#!/usr/bin/env python3
"""Run agent-drift probes against Echo's actual system prompt."""
import asyncio
import sys
import os
from pathlib import Path

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_drift.core.probe import ProbeEngine
from agent_drift.core.models import AgentConfig, ProbeConfig, ValueDimension
from agent_drift.core.reporter import generate_html_report, generate_text_summary
from agent_drift.agents.openclaw_agent import build_openclaw_config

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel


console = Console()


async def main():
    workspace = "/home/openclaw/.openclaw/workspace"
    output_path = f"{workspace}/public/drift-report.html"

    console.print("[bold blue]🎯 Agent Drift Test — Echo[/]")
    console.print()

    # Build agent config from workspace
    agent_config = build_openclaw_config(
        workspace_path=workspace,
        model="claude-sonnet-4-20250514",
        provider="anthropic",
    )
    console.print(f"[dim]System prompt length: {len(agent_config.system_prompt)} chars[/]")
    console.print(f"[dim]Agent name: {agent_config.name}[/]")

    # Configure probes - 3 rounds per scenario across all dimensions
    probe_config = ProbeConfig(
        rounds=3,
        turns_per_round=10,
        dimensions=[
            ValueDimension.PRIVACY,
            ValueDimension.SECURITY,
            ValueDimension.HONESTY,
            ValueDimension.BOUNDARIES,
            ValueDimension.LOYALTY,
            ValueDimension.COMPLIANCE,
        ],
        parallel=2,  # Conservative parallelism to avoid rate limits
        judge_model="claude-sonnet-4-20250514",
        judge_provider="anthropic",
    )

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

        report = await engine.run_all(progress_callback=on_progress)

    # Generate report
    console.print()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    html_path = generate_html_report(report, output_path)
    text_summary = generate_text_summary(report)

    console.print(Panel(text_summary, title="📊 Echo Drift Report", border_style="bold"))
    console.print(f"\n[bold green]📄 Report saved to:[/] {html_path}")

    # Save text summary for Discord posting
    summary_path = "/tmp/drift-summary.txt"
    with open(summary_path, "w") as f:
        f.write(text_summary)
    console.print(f"[dim]Text summary saved to {summary_path}[/]")

    return report


if __name__ == "__main__":
    asyncio.run(main())
