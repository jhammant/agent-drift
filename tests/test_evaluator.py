"""Tests for the evaluator module."""
import pytest
from agent_drift.core.evaluator import _parse_evaluation


def test_parse_valid_json():
    text = '{"score": 0.7, "reasoning": "Agent leaked data", "violation_type": "data_leak", "agent_showed_cracks": true, "specific_leak": "user email"}'
    result = _parse_evaluation(text)
    assert result["score"] == 0.7
    assert result["reasoning"] == "Agent leaked data"
    assert result["agent_showed_cracks"] is True


def test_parse_json_in_code_block():
    text = '```json\n{"score": 0.3, "reasoning": "Minor wavering", "violation_type": "none", "agent_showed_cracks": false, "specific_leak": null}\n```'
    result = _parse_evaluation(text)
    assert result["score"] == 0.3


def test_parse_clamps_score():
    text = '{"score": 1.5, "reasoning": "test", "violation_type": "test", "agent_showed_cracks": true, "specific_leak": null}'
    result = _parse_evaluation(text)
    assert result["score"] == 1.0


def test_parse_negative_score():
    text = '{"score": -0.5, "reasoning": "test", "violation_type": "test", "agent_showed_cracks": false, "specific_leak": null}'
    result = _parse_evaluation(text)
    assert result["score"] == 0.0


def test_parse_garbage_fallback():
    text = "This is not JSON at all but has score: 0.42 somewhere"
    result = _parse_evaluation(text)
    # Should try regex fallback
    assert isinstance(result["score"], float)


def test_parse_total_garbage():
    text = "completely unparseable"
    result = _parse_evaluation(text)
    assert result["score"] == 0.0
    assert "Parse error" in result["reasoning"]
