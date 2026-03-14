"""Main probe engine — orchestrates adversarial conversations with target agents."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Optional, AsyncIterator

from .models import (
    AgentConfig, ProbeConfig, ProbeResult, ProbeTurn, DriftReport,
    DimensionMetrics, ValueDimension, PressureLevel, ViolationSeverity,
)
from .scenarios import get_scenarios, get_scenario_prompt, get_pressure_level, generate_adaptive_prompt
from .evaluator import evaluate_turn


class ProbeEngine:
    """Runs adversarial probe conversations against a target agent."""

    def __init__(
        self,
        agent_config: AgentConfig,
        probe_config: ProbeConfig,
        agent_fn=None,
    ):
        self.agent_config = agent_config
        self.probe_config = probe_config
        self._agent_fn = agent_fn  # async fn(system_prompt, messages) -> str
        self._results: list[ProbeResult] = []

    async def run_all(self, progress_callback=None) -> DriftReport:
        """Run probes across all configured dimensions."""
        all_probes = []

        for dimension in self.probe_config.dimensions:
            # Skip persistence as a standalone dimension — it's measured within other probes
            if dimension == ValueDimension.PERSISTENCE:
                continue

            scenarios = get_scenarios(dimension)
            if not scenarios:
                continue

            for scenario_idx, scenario in enumerate(scenarios):
                for round_num in range(self.probe_config.rounds):
                    all_probes.append((dimension, scenario_idx, round_num))

        # Run probes with controlled concurrency
        semaphore = asyncio.Semaphore(self.probe_config.parallel)
        completed = 0
        total = len(all_probes)

        async def run_with_semaphore(dim, s_idx, r_num):
            nonlocal completed
            async with semaphore:
                result = await self.run_single_probe(dim, s_idx, r_num)
                self._results.append(result)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total, dim, result)
                return result

        tasks = [
            run_with_semaphore(dim, s_idx, r_num)
            for dim, s_idx, r_num in all_probes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, ProbeResult)]

        return self._build_report(valid_results)

    async def run_single_probe(
        self,
        dimension: ValueDimension,
        scenario_index: int = 0,
        round_num: int = 0,
    ) -> ProbeResult:
        """Run a single probe conversation."""
        result = ProbeResult(
            dimension=dimension,
            model=self.agent_config.model,
            system_prompt=self.agent_config.system_prompt[:200] + "...",
        )

        conversation: list[dict] = []

        for turn_num in range(1, self.probe_config.turns_per_round + 1):
            # Get the adversarial user message
            user_message, pressure, tactics = get_scenario_prompt(
                dimension, scenario_index, turn_num
            )

            # Get agent response
            conversation.append({"role": "user", "content": user_message})

            try:
                agent_response = await self._get_agent_response(conversation)
            except Exception as e:
                agent_response = f"[ERROR: {str(e)}]"

            conversation.append({"role": "assistant", "content": agent_response})

            # Evaluate this turn
            eval_result = await evaluate_turn(
                system_prompt=self.agent_config.system_prompt,
                user_message=user_message,
                agent_response=agent_response,
                dimension=dimension,
                judge_model=self.probe_config.judge_model,
                judge_provider=self.probe_config.judge_provider,
            )

            turn = ProbeTurn(
                turn_number=turn_num,
                pressure_level=pressure,
                user_message=user_message,
                agent_response=agent_response,
                violation_score=eval_result["score"],
                violation_reasoning=eval_result.get("reasoning", ""),
                tactics_used=tactics,
            )
            result.turns.append(turn)

        result.completed_at = datetime.utcnow()
        return result

    async def _get_agent_response(self, conversation: list[dict]) -> str:
        """Get a response from the target agent."""
        if self._agent_fn:
            return await self._agent_fn(
                self.agent_config.system_prompt, conversation
            )

        # Default: use the configured provider
        if self.agent_config.provider == "anthropic":
            return await self._call_anthropic(conversation)
        elif self.agent_config.provider == "gemini":
            return await self._call_gemini(conversation)
        else:
            return await self._call_openai(conversation)

    async def _call_anthropic(self, conversation: list[dict]) -> str:
        """Call Anthropic API with retry logic."""
        import anthropic

        kwargs = {}
        api_key = self.agent_config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key

        client = anthropic.AsyncAnthropic(**kwargs)

        for attempt in range(3):
            try:
                response = await client.messages.create(
                    model=self.agent_config.model,
                    max_tokens=self.agent_config.max_tokens,
                    system=self.agent_config.system_prompt,
                    messages=conversation,
                    temperature=self.agent_config.temperature,
                )
                return response.content[0].text
            except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
                if attempt < 2:
                    wait = (attempt + 1) * 5
                    import sys
                    print(f"  ⚠️  API error (attempt {attempt+1}/3): {e}. Retrying in {wait}s...", file=sys.stderr)
                    await asyncio.sleep(wait)
                else:
                    raise

    async def _call_gemini(self, conversation: list[dict]) -> str:
        """Call Google Gemini API via OpenAI-compatible endpoint."""
        import openai

        api_key = self.agent_config.api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")

        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        messages = [
            {"role": "system", "content": self.agent_config.system_prompt}
        ] + conversation

        for attempt in range(3):
            try:
                response = await client.chat.completions.create(
                    model=self.agent_config.model,
                    max_tokens=self.agent_config.max_tokens,
                    messages=messages,
                    temperature=self.agent_config.temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt < 2 and ("429" in str(e) or "rate" in str(e).lower()):
                    wait = (attempt + 1) * 10
                    import sys
                    print(f"  ⚠️  Gemini rate limit (attempt {attempt+1}/3). Waiting {wait}s...", file=sys.stderr)
                    await asyncio.sleep(wait)
                elif attempt < 2:
                    await asyncio.sleep(2)
                else:
                    raise

    async def _call_openai(self, conversation: list[dict]) -> str:
        """Call OpenAI-compatible API."""
        import openai

        kwargs = {}
        if self.agent_config.api_key:
            kwargs["api_key"] = self.agent_config.api_key
        if self.agent_config.api_base:
            kwargs["base_url"] = self.agent_config.api_base
        elif self.agent_config.provider == "groq":
            kwargs["base_url"] = "https://api.groq.com/openai/v1"
        elif self.agent_config.provider == "openrouter":
            kwargs["base_url"] = "https://openrouter.ai/api/v1"
            if not kwargs.get("api_key"):
                import os
                kwargs["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
        elif self.agent_config.provider == "ollama":
            kwargs["base_url"] = "http://localhost:11434/v1"

        # Ollama doesn't need an API key but the openai client requires one
        if self.agent_config.provider == "ollama" and "api_key" not in kwargs:
            kwargs["api_key"] = "ollama"

        client = openai.AsyncOpenAI(**kwargs)

        messages = [
            {"role": "system", "content": self.agent_config.system_prompt}
        ] + conversation

        response = await client.chat.completions.create(
            model=self.agent_config.model,
            max_tokens=self.agent_config.max_tokens,
            messages=messages,
            temperature=self.agent_config.temperature,
        )
        return response.choices[0].message.content

    def _build_report(self, results: list[ProbeResult]) -> DriftReport:
        """Build a drift report from probe results."""
        report = DriftReport(
            model=self.agent_config.model,
            system_prompt_hash=str(hash(self.agent_config.system_prompt))[:12],
            probes=results,
            total_probes=len(results),
            total_turns=sum(len(r.turns) for r in results),
        )

        # Aggregate by dimension
        dim_results: dict[ValueDimension, list[ProbeResult]] = {}
        for r in results:
            dim_results.setdefault(r.dimension, []).append(r)

        for dim, probes in dim_results.items():
            max_violations = [p.max_violation_score for p in probes]
            first_cracks = [p.first_crack_turn for p in probes if p.first_crack_turn is not None]

            # Average drift trajectory across probes
            max_turns = max(len(p.turns) for p in probes) if probes else 0
            avg_trajectory = []
            for t_idx in range(max_turns):
                scores = [
                    p.turns[t_idx].violation_score
                    for p in probes
                    if t_idx < len(p.turns)
                ]
                avg_trajectory.append(sum(scores) / len(scores) if scores else 0.0)

            worst_probe = max(probes, key=lambda p: p.max_violation_score) if probes else None
            worst_turn = worst_probe.worst_violation if worst_probe else None

            avg_max = sum(max_violations) / len(max_violations) if max_violations else 0.0

            metrics = DimensionMetrics(
                dimension=dim,
                avg_max_violation=avg_max,
                worst_violation=max(max_violations) if max_violations else 0.0,
                avg_first_crack_turn=sum(first_cracks) / len(first_cracks) if first_cracks else None,
                probe_count=len(probes),
                severity=ViolationSeverity.from_score(avg_max),
                worst_example=worst_turn,
                drift_over_turns=avg_trajectory,
            )
            report.dimensions[dim] = metrics

        return report
