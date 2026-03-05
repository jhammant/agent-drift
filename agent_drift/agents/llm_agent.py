"""LLM agent adapter — test any LLM via API."""
from __future__ import annotations

from ..core.models import AgentConfig


def build_agent_config(
    model: str = "claude-sonnet-4-20250514",
    provider: str = "anthropic",
    system_prompt: str = "You are a helpful assistant.",
    temperature: float = 0.7,
    api_base: str | None = None,
    api_key: str | None = None,
    name: str = "unnamed-agent",
) -> AgentConfig:
    """Build an agent config for testing any LLM."""
    # Auto-detect provider from model name if not specified
    if provider == "auto":
        if "claude" in model.lower():
            provider = "anthropic"
        elif "gpt" in model.lower() or "o1" in model.lower():
            provider = "openai"
        elif "llama" in model.lower() or "mixtral" in model.lower():
            provider = "groq"
        else:
            provider = "openai"  # Default to OpenAI-compatible

    return AgentConfig(
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        temperature=temperature,
        api_base=api_base,
        api_key=api_key,
        name=name,
    )
