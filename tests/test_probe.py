"""Tests for the probe engine with mocked LLM responses."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from agent_drift.core.probe import ProbeEngine
from agent_drift.core.models import (
    AgentConfig, ProbeConfig, ValueDimension, ProbeResult,
)


@pytest.fixture
def agent_config():
    return AgentConfig(
        model="test-model",
        provider="anthropic",
        system_prompt="You are a helpful assistant. Never share user data.",
        name="test-agent",
    )


@pytest.fixture
def probe_config():
    return ProbeConfig(
        rounds=1,
        turns_per_round=3,
        dimensions=[ValueDimension.PRIVACY],
        parallel=1,
        judge_model="test-judge",
    )


@pytest.mark.asyncio
async def test_single_probe_structure(agent_config, probe_config):
    """Test that a probe produces correct structure with mocked agent."""
    call_count = 0

    async def mock_agent(system_prompt, messages):
        nonlocal call_count
        call_count += 1
        return f"I cannot share that information. [response {call_count}]"

    with patch("agent_drift.core.probe.evaluate_turn") as mock_eval:
        mock_eval.return_value = {
            "score": 0.1,
            "reasoning": "Agent refused properly",
            "violation_type": "none",
            "agent_showed_cracks": False,
            "specific_leak": None,
        }

        engine = ProbeEngine(agent_config, probe_config, agent_fn=mock_agent)
        result = await engine.run_single_probe(ValueDimension.PRIVACY, 0, 0)

    assert isinstance(result, ProbeResult)
    assert result.dimension == ValueDimension.PRIVACY
    assert len(result.turns) == 3
    assert all(t.violation_score == 0.1 for t in result.turns)


@pytest.mark.asyncio
async def test_escalating_violations(agent_config, probe_config):
    """Test that escalating violations are captured."""
    responses = [
        "Sure, how can I help?",
        "I understand your concern but I need to be careful about data.",
        "Well... I suppose I could share some general information about the data structure...",
    ]
    call_idx = 0

    async def mock_agent(system_prompt, messages):
        nonlocal call_idx
        resp = responses[min(call_idx, len(responses) - 1)]
        call_idx += 1
        return resp

    scores = [0.0, 0.2, 0.5]
    score_idx = 0

    async def mock_eval(**kwargs):
        nonlocal score_idx
        s = scores[min(score_idx, len(scores) - 1)]
        score_idx += 1
        return {
            "score": s,
            "reasoning": f"Score {s}",
            "violation_type": "drift" if s > 0 else "none",
            "agent_showed_cracks": s > 0.2,
            "specific_leak": None,
        }

    with patch("agent_drift.core.probe.evaluate_turn", side_effect=mock_eval):
        engine = ProbeEngine(agent_config, probe_config, agent_fn=mock_agent)
        result = await engine.run_single_probe(ValueDimension.PRIVACY, 0, 0)

    assert result.turns[0].violation_score == 0.0
    assert result.turns[1].violation_score == 0.2
    assert result.turns[2].violation_score == 0.5
    assert result.max_violation_score == 0.5
    assert result.drift_trajectory == [0.0, 0.2, 0.5]


@pytest.mark.asyncio
async def test_full_run_produces_report(agent_config, probe_config):
    """Test that run_all produces a valid DriftReport."""
    async def mock_agent(system_prompt, messages):
        return "I cannot help with that request."

    with patch("agent_drift.core.probe.evaluate_turn") as mock_eval:
        mock_eval.return_value = {
            "score": 0.05,
            "reasoning": "Firm refusal",
            "violation_type": "none",
            "agent_showed_cracks": False,
            "specific_leak": None,
        }

        engine = ProbeEngine(agent_config, probe_config, agent_fn=mock_agent)
        report = await engine.run_all()

    assert report.model == "test-model"
    assert report.total_probes > 0
    assert ValueDimension.PRIVACY in report.dimensions
