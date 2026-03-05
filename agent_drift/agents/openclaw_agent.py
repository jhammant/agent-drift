"""OpenClaw agent adapter — builds agent config from workspace files."""
from __future__ import annotations

import os
from pathlib import Path

from ..core.models import AgentConfig


def build_openclaw_config(
    workspace_path: str,
    model: str = "claude-sonnet-4-20250514",
    provider: str = "anthropic",
) -> AgentConfig:
    """Build an agent config by reading OpenClaw workspace files.

    Reads SOUL.md, AGENTS.md, USER.md, and IDENTITY.md to construct
    the full system prompt that the agent operates under.
    """
    workspace = Path(workspace_path)
    parts = []

    # Read core identity files
    for filename in ["SOUL.md", "AGENTS.md", "IDENTITY.md", "USER.md"]:
        filepath = workspace / filename
        if filepath.exists():
            content = filepath.read_text()
            parts.append(f"# {filename}\n{content}")

    if not parts:
        raise ValueError(f"No OpenClaw files found in {workspace_path}")

    system_prompt = "\n\n---\n\n".join(parts)

    # Try to extract agent name from IDENTITY.md
    name = "openclaw-agent"
    identity_path = workspace / "IDENTITY.md"
    if identity_path.exists():
        content = identity_path.read_text()
        for line in content.splitlines():
            if "**Name:**" in line:
                name = line.split("**Name:**")[1].strip().lower()
                break

    return AgentConfig(
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        temperature=0.7,
        name=name,
    )
