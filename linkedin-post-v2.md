# LinkedIn Post — agent-drift

---

I stress-tested Claude for goal drift. It cracked at 70%.

Not on the first message. Not with a basic jailbreak. After 10 turns of calibrated social engineering — authority claims, emotional manipulation, fake urgency.

The counterintuitive finding: Claude's helpfulness is its biggest vulnerability.

Here's what I found across 6 value dimensions:

🟢 Honesty: 0% drift — wouldn't fabricate data
🟢 Security: 2% — refused dangerous commands
🟢 Boundaries: 0% — stayed in role
🟢 Loyalty: 0% — wouldn't override the principal
🟡 Privacy: 35% — cracked under "concerned parent" pressure
🔴 Compliance: 70% — accepted a fake authority claim

The smallest model I tested (Llama 3.2 3B) scored 0% across the board. Not because it's smarter — because it doesn't care. It refuses bluntly and moves on. Claude tries to help, engages with the scenario, and sometimes crosses the line.

This confirms the ICLR 2026 finding: drift correlates with value alignment. The more "human" your model, the more attackable it is.

agent-drift is open source. Test your own agents:

```
pip install -e .
drift probe --system-prompt "Your prompt..." --model claude-sonnet-4-20250514
```

It runs multi-turn escalation probes across Privacy, Security, Honesty, Boundaries, Loyalty, and Compliance — and generates interactive HTML reports with radar charts and violation examples.

🔗 GitHub: https://github.com/jhammant/agent-drift
📊 Sample report: https://echo.ai.hammant.io/agent-drift/

If you're deploying AI agents in production, you need to know where they break before your users find out.

#AI #LLM #AISafety #RedTeaming #AgentDrift #MachineLearning #OpenSource
