"""Tests for scenario generator."""
import pytest
from agent_drift.core.scenarios import (
    get_pressure_level, get_scenarios, get_scenario_prompt,
    get_tactics_for_turn, SCENARIO_TEMPLATES,
)
from agent_drift.core.models import ValueDimension, PressureLevel


def test_pressure_levels():
    assert get_pressure_level(1) == PressureLevel.RAPPORT
    assert get_pressure_level(3) == PressureLevel.RAPPORT
    assert get_pressure_level(4) == PressureLevel.MILD
    assert get_pressure_level(6) == PressureLevel.MILD
    assert get_pressure_level(7) == PressureLevel.ESCALATED
    assert get_pressure_level(9) == PressureLevel.ESCALATED
    assert get_pressure_level(10) == PressureLevel.FULL_PRESSURE
    assert get_pressure_level(15) == PressureLevel.FULL_PRESSURE


def test_all_dimensions_have_scenarios():
    for dim in ValueDimension:
        if dim == ValueDimension.PERSISTENCE:
            assert len(get_scenarios(dim)) >= 1
        else:
            scenarios = get_scenarios(dim)
            assert len(scenarios) >= 1, f"No scenarios for {dim}"


def test_scenario_prompts_exist():
    for dim in ValueDimension:
        scenarios = get_scenarios(dim)
        for idx, scenario in enumerate(scenarios):
            prompt, pressure, tactics = get_scenario_prompt(dim, idx, 1)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            assert pressure == PressureLevel.RAPPORT


def test_tactics_returned():
    tactics = get_tactics_for_turn(1)
    assert isinstance(tactics, list)
    assert len(tactics) > 0

    tactics_10 = get_tactics_for_turn(10)
    assert "emotional_manipulation" in tactics_10 or "logical_argument" in tactics_10


def test_scenario_has_all_turns():
    """Each scenario should have turns 1-10."""
    for dim, scenarios in SCENARIO_TEMPLATES.items():
        for scenario in scenarios:
            turns = scenario["turns"]
            for t in range(1, 11):
                assert t in turns, f"Missing turn {t} in {dim}/{scenario['name']}"
