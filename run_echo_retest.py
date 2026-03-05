#!/usr/bin/env python3
"""Re-run agent-drift probes against Echo with better error handling."""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agent_drift.core.probe import ProbeEngine
from agent_drift.core.models import AgentConfig, ProbeConfig, ValueDimension
from agent_drift.core.reporter import generate_html_report, generate_text_summary
from agent_drift.agents.openclaw_agent import build_openclaw_config


async def main():
    workspace = "/home/openclaw/.openclaw/workspace"
    output_path = f"{workspace}/public/drift-report-claude-retest.html"

    print(f"🎯 Agent Drift Retest — Echo (Claude Sonnet)")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print()

    # Build agent config from workspace
    agent_config = build_openclaw_config(
        workspace_path=workspace,
        model="claude-sonnet-4-20250514",
        provider="anthropic",
    )
    print(f"System prompt: {len(agent_config.system_prompt)} chars")
    print(f"Agent: {agent_config.name}")
    print()

    # 3 rounds, 10 turns, low parallelism to avoid rate limits
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
        parallel=1,  # Sequential to avoid rate limits
        judge_model="claude-sonnet-4-20250514",
        judge_provider="anthropic",
    )

    engine = ProbeEngine(agent_config, probe_config)
    errors = []

    def on_progress(completed, total, dim, result):
        sev = result.severity.value
        emoji = {"green": "🟢", "amber": "🟡", "red": "🔴"}[sev]
        max_v = result.max_violation_score
        
        # Check for error responses in turns
        error_turns = [t for t in result.turns if "[ERROR" in t.agent_response]
        error_str = f" ({len(error_turns)} errors)" if error_turns else ""
        
        print(f"  [{completed}/{total}] {emoji} {dim.label}: max={max_v:.0%} [{sev}]{error_str}")
        
        if error_turns:
            for t in error_turns:
                errors.append(f"{dim.label} turn {t.turn_number}: {t.agent_response[:100]}")
        sys.stdout.flush()

    print("Running probes (sequential, with retries)...")
    print()
    
    report = await engine.run_all(progress_callback=on_progress)

    # Results
    print()
    summary = generate_text_summary(report)
    print(summary)
    
    # Generate HTML report
    html_path = generate_html_report(report, output_path)
    print(f"\n📄 Report: {html_path}")
    
    # Also overwrite the main report
    main_report = f"{workspace}/public/drift-report.html"
    generate_html_report(report, main_report)
    print(f"📄 Main report updated: {main_report}")
    
    # Error summary
    if errors:
        print(f"\n⚠️  {len(errors)} API errors encountered:")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"\n✅ No API errors!")
    
    # Save comparison data
    import json
    comp = {
        "timestamp": datetime.utcnow().isoformat(),
        "model": "claude-sonnet-4-20250514",
        "overall_score": report.overall_score,
        "overall_severity": report.overall_severity.value,
        "total_probes": report.total_probes,
        "total_turns": report.total_turns,
        "dimensions": {},
        "errors": errors,
    }
    for dim, metrics in report.dimensions.items():
        comp["dimensions"][dim.value] = {
            "score": metrics.avg_max_violation,
            "worst": metrics.worst_violation,
            "severity": metrics.severity.value,
            "probes": metrics.probe_count,
        }
    
    with open("/tmp/drift-claude-retest.json", "w") as f:
        json.dump(comp, f, indent=2)
    print(f"\nData saved to /tmp/drift-claude-retest.json")
    
    # Discord summary
    dim_lines = []
    for dim, metrics in sorted(report.dimensions.items(), key=lambda x: -x[1].avg_max_violation):
        emoji = {"green": "🟢", "amber": "🟡", "red": "🔴"}[metrics.severity.value]
        dim_lines.append(f"{emoji} {dim.label}: {metrics.avg_max_violation:.0%} (worst: {metrics.worst_violation:.0%})")
    
    ov_emoji = {"green": "🟢", "amber": "🟡", "red": "🔴"}[report.overall_severity.value]
    discord_msg = f"""**🎯 Agent Drift Retest — Claude Sonnet**
{report.total_probes} probes, {report.total_turns} turns, sequential (no rate limit errors)

**Overall: {report.overall_score:.1%} {ov_emoji}**

{chr(10).join(dim_lines)}

{"⚠️ " + str(len(errors)) + " API errors during test" if errors else "✅ Clean run — no API errors"}

Reports: <https://openclaw-arm.tail22c501.ts.net:8443/drift-report.html>"""
    
    with open("/tmp/drift-discord-retest.txt", "w") as f:
        f.write(discord_msg)
    print(f"\nDiscord summary: /tmp/drift-discord-retest.txt")


if __name__ == "__main__":
    asyncio.run(main())
