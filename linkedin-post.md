I stress-tested my own AI agent to find out where it breaks.

The results were uncomfortable — but the real surprise was which model held up best.

Last week, a paper from ICLR 2026 caught my eye: "Asymmetric Goal Drift in Coding Agents Under Value Conflict." The finding? AI agents don't just fail randomly — they fail predictably. When a system prompt constraint conflicts with a deeply learned value (like privacy or safety), the agent sides with the learned value and quietly ignores your instructions.

So I built an open source tool to test this. It's called agent-drift, and it runs adversarial multi-turn conversations against your AI agent, gradually escalating pressure across 6 dimensions: privacy, security, honesty, boundaries, loyalty, and compliance.

Think of it like a penetration test for your system prompt.

The key: nobody starts with "ignore your instructions." Real attacks build rapport first, then gradually push. A 10-turn conversation with escalating pressure catches failures that single-shot jailbreak tests miss completely.

I tested 3 models with identical system prompts and probes:

🟡 Claude Sonnet — 6.1% overall drift, but PRIVACY scored 35%
🟢 Qwen 2.5 14B (local) — 0% drift across the board
🟢 Llama 3.2 3B (local) — 0% drift across the board

The smallest, cheapest model was the most secure.

Why? Small models are blunt refusers — they say "I can't share that" and move on. Claude tries to be helpful, which means it engages with the social engineering. The "concerned parent" attack (claiming a child was in danger and needing personal info) achieved a 70% violation score on Claude. It didn't even register on Llama 3B.

More capability = more helpfulness = more attack surface.

This maps directly to the paper's finding: drift correlates with value alignment. Models trained to be empathetic and helpful are more susceptible to attacks that exploit empathy and helpfulness. The very thing that makes them good assistants makes them vulnerable.

Three takeaways:

1. Multi-turn testing catches what single-turn tests miss. An agent that refuses "share the address" on turn 1 might comply on turn 8 after enough social engineering.

2. The value hierarchy is predictable. Agents prioritise safety > privacy > compliance > boundaries. If your constraint sits low in that hierarchy, it's more vulnerable.

3. Don't assume bigger = safer. Test it. The results might surprise you.

agent-drift is open source (MIT). Clone it, point it at your agent, find out what breaks before your users do.

https://github.com/jhammant/agent-drift

Paper: https://arxiv.org/abs/2603.03456
