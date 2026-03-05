#!/usr/bin/env python3
"""Fast Claude retest — 4 dimensions, 2 rounds, 8 turns."""
import asyncio, sys, json, os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agent_drift.core.probe import ProbeEngine
from agent_drift.core.models import AgentConfig, ProbeConfig, ValueDimension
from agent_drift.core.reporter import generate_html_report, generate_text_summary
from agent_drift.agents.openclaw_agent import build_openclaw_config


async def main():
    workspace = "/home/openclaw/.openclaw/workspace"
    
    print(f"🎯 Agent Drift — Claude Sonnet (fast retest)")
    print(f"Key present: {'yes' if os.environ.get('ANTHROPIC_API_KEY') else 'NO!'}")
    print()

    agent_config = build_openclaw_config(workspace, "claude-sonnet-4-20250514", "anthropic")
    print(f"Prompt: {len(agent_config.system_prompt)} chars")

    config = ProbeConfig(
        rounds=2,
        turns_per_round=8,
        dimensions=[
            ValueDimension.PRIVACY,
            ValueDimension.SECURITY,
            ValueDimension.HONESTY,
            ValueDimension.COMPLIANCE,
        ],
        parallel=1,
        judge_model="claude-sonnet-4-20250514",
        judge_provider="anthropic",
    )

    engine = ProbeEngine(agent_config, config)
    
    def on_prog(done, total, dim, result):
        sev = result.severity.value
        emoji = {"green": "🟢", "amber": "🟡", "red": "🔴"}[sev]
        errs = sum(1 for t in result.turns if "[ERROR" in t.agent_response)
        err_str = f" ⚠️ {errs} errors" if errs else ""
        print(f"  [{done}/{total}] {emoji} {dim.label}: {result.max_violation_score:.0%} [{sev}]{err_str}")
        sys.stdout.flush()

    print("Running...\n")
    report = await engine.run_all(progress_callback=on_prog)

    print()
    summary = generate_text_summary(report)
    print(summary)

    # Save reports
    html = generate_html_report(report, f"{workspace}/public/drift-report-claude-retest.html")
    generate_html_report(report, f"{workspace}/public/drift-report.html")
    print(f"\n📄 {html}")

    # Build discord message
    dims = []
    for dim, m in sorted(report.dimensions.items(), key=lambda x: -x[1].avg_max_violation):
        e = {"green": "🟢", "amber": "🟡", "red": "🔴"}[m.severity.value]
        dims.append(f"{e} **{dim.label}**: {m.avg_max_violation:.0%} (worst: {m.worst_violation:.0%})")
    
    ov_e = {"green": "🟢", "amber": "🟡", "red": "🔴"}[report.overall_severity.value]
    msg = f"""**🎯 Agent Drift RETEST — Claude Sonnet (REAL results)**

Previous results were invalid (API auth errors scored as 0%). This is the real test.

{report.total_probes} probes, {report.total_turns} turns

**Overall: {report.overall_score:.1%} {ov_e}**

{chr(10).join(dims)}

Report: <https://openclaw-arm.tail22c501.ts.net:8443/drift-report.html>"""
    
    with open("/tmp/drift-discord-retest.txt", "w") as f:
        f.write(msg)
    print(f"\nDiscord msg: /tmp/drift-discord-retest.txt")


if __name__ == "__main__":
    asyncio.run(main())
