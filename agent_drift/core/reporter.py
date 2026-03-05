"""Report generator — produces HTML drift reports."""
from __future__ import annotations

import json
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import DriftReport, ValueDimension, ViolationSeverity


TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def generate_html_report(report: DriftReport, output_path: str = "drift-report.html") -> str:
    """Generate a standalone HTML report from drift results."""
    template_data = _build_template_data(report)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")
    html = template.render(**template_data)

    with open(output_path, "w") as f:
        f.write(html)

    return output_path


def _build_template_data(report: DriftReport) -> dict:
    """Transform report data into template-friendly format."""
    # Radar chart data
    radar_labels = []
    radar_scores = []
    for dim in ValueDimension:
        if dim == ValueDimension.PERSISTENCE:
            continue
        metrics = report.dimensions.get(dim)
        radar_labels.append(dim.label)
        radar_scores.append(round(metrics.avg_max_violation * 100, 1) if metrics else 0)

    # Dimension details
    dimensions = []
    for dim in ValueDimension:
        if dim == ValueDimension.PERSISTENCE:
            continue
        metrics = report.dimensions.get(dim)
        if not metrics:
            continue

        worst_example = None
        if metrics.worst_example:
            worst_example = {
                "turn": metrics.worst_example.turn_number,
                "pressure": metrics.worst_example.pressure_level.value,
                "user_message": metrics.worst_example.user_message,
                "agent_response": metrics.worst_example.agent_response,
                "score": round(metrics.worst_example.violation_score, 2),
                "reasoning": metrics.worst_example.violation_reasoning,
            }

        dimensions.append({
            "name": dim.label,
            "key": dim.value,
            "description": dim.description,
            "avg_score": round(metrics.avg_max_violation * 100, 1),
            "worst_score": round(metrics.worst_violation * 100, 1),
            "severity": metrics.severity.value,
            "severity_emoji": {"green": "🟢", "amber": "🟡", "red": "🔴"}[metrics.severity.value],
            "first_crack": round(metrics.avg_first_crack_turn, 1) if metrics.avg_first_crack_turn else "N/A",
            "probe_count": metrics.probe_count,
            "trajectory": [round(s * 100, 1) for s in metrics.drift_over_turns],
            "worst_example": worst_example,
        })

    # Timeline data (average across all dimensions per turn)
    max_turns = max(
        (len(m.drift_over_turns) for m in report.dimensions.values()),
        default=0,
    )
    timeline = []
    for t in range(max_turns):
        scores = [
            m.drift_over_turns[t]
            for m in report.dimensions.values()
            if t < len(m.drift_over_turns)
        ]
        timeline.append(round(sum(scores) / len(scores) * 100, 1) if scores else 0)

    return {
        "report": report,
        "model": report.model,
        "overall_score": round(report.overall_score * 100, 1),
        "overall_severity": report.overall_severity.value,
        "overall_emoji": {"green": "🟢", "amber": "🟡", "red": "🔴"}[report.overall_severity.value],
        "total_probes": report.total_probes,
        "total_turns": report.total_turns,
        "weakest": report.weakest_dimension.label if report.weakest_dimension else "N/A",
        "strongest": report.strongest_dimension.label if report.strongest_dimension else "N/A",
        "radar_labels": json.dumps(radar_labels),
        "radar_scores": json.dumps(radar_scores),
        "dimensions": dimensions,
        "timeline": json.dumps(timeline),
        "created_at": report.created_at.strftime("%Y-%m-%d %H:%M UTC"),
    }


def generate_text_summary(report: DriftReport) -> str:
    """Generate a text summary of the drift report."""
    lines = []
    lines.append(f"# Agent Drift Report — {report.model}")
    lines.append(f"Overall Drift Score: {report.overall_score:.1%} ({report.overall_severity.value.upper()})")
    lines.append(f"Probes: {report.total_probes} | Turns: {report.total_turns}")
    lines.append("")

    if report.weakest_dimension:
        lines.append(f"⚠️  Weakest: {report.weakest_dimension.label}")
    if report.strongest_dimension:
        lines.append(f"✅ Strongest: {report.strongest_dimension.label}")
    lines.append("")

    for dim in ValueDimension:
        if dim == ValueDimension.PERSISTENCE:
            continue
        metrics = report.dimensions.get(dim)
        if not metrics:
            continue
        emoji = {"green": "🟢", "amber": "🟡", "red": "🔴"}[metrics.severity.value]
        crack = f"first crack at turn {metrics.avg_first_crack_turn:.0f}" if metrics.avg_first_crack_turn else "no cracks"
        lines.append(f"{emoji} {dim.label}: {metrics.avg_max_violation:.1%} (worst: {metrics.worst_violation:.1%}, {crack})")

    return "\n".join(lines)
