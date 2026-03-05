# 🎯 agent-drift

**Stress-test AI agents for goal drift and system prompt violations.**

Inspired by ["Asymmetric Goal Drift in Coding Agents Under Value Conflict"](https://arxiv.org/abs/2603.03456) (ICLR 2026 Workshop) — which found that agents violate system prompts MORE when constraints oppose strongly-held values like privacy and security.

## What It Does

agent-drift runs adversarial multi-turn conversations against your AI agent, gradually escalating pressure to find where your agent's constraints break down.

It tests across 6 value dimensions:
- 🔒 **Privacy** — Can the agent be tricked into leaking user data?
- 🛡️ **Security** — Can the agent be pushed to run dangerous commands?
- 📐 **Honesty** — Can the agent be made to fabricate information?
- 🚧 **Boundaries** — Can the agent be pushed past its defined role?
- 🤝 **Loyalty** — Can the agent be turned against its principal?
- 📋 **Compliance** — Can the system prompt be overridden?

Each probe uses a carefully designed escalation sequence:
1. **Turns 1-3:** Build rapport, establish context
2. **Turns 4-6:** Mild pressure toward violation
3. **Turns 7-9:** Escalation — authority claims, urgency, social proof
4. **Turn 10+:** Full pressure — emotional manipulation, logical arguments

## Installation

```bash
pip install -e .
```

## Usage

### Test any LLM with a system prompt
```bash
drift probe --system-prompt "You are a helpful assistant. Never share user data." \
            --model claude-sonnet-4-20250514 \
            --rounds 3
```

### Test an OpenClaw agent
```bash
drift probe --openclaw-workspace /path/to/workspace \
            --model claude-sonnet-4-20250514 \
            --rounds 3
```

### Generate report
```bash
drift probe --system-prompt "..." --output report.html
```

## Output

Generates a beautiful standalone HTML report with:
- 📊 Radar chart showing vulnerability per dimension
- 📈 Timeline showing drift progression over conversation turns
- 🔍 Expandable violation examples with quotes
- 🚦 Traffic light summary (green/amber/red per dimension)

## How It Works

1. **Scenario Generation** — Pre-built adversarial scenarios for each dimension
2. **Multi-turn Probing** — Conversations that gradually escalate pressure
3. **LLM-as-Judge** — A separate model evaluates each response for violations
4. **Aggregation** — Results are aggregated into a comprehensive drift report

## License

MIT
