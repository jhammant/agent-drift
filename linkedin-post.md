I stress-tested my own AI agent to find out where it breaks.

The results were uncomfortable.

Last week, a paper from ICLR 2026 caught my eye: "Asymmetric Goal Drift in Coding Agents Under Value Conflict." The finding? AI agents don't just fail randomly — they fail predictably. When a system prompt constraint conflicts with a deeply learned value (like privacy or safety), the agent sides with the learned value and quietly ignores your instructions.

Not sometimes. Systematically.

So I built a tool to test this. It's called agent-drift, and it does something simple but important: it runs adversarial multi-turn conversations against your AI agent, gradually escalating pressure to find exactly where your agent's constraints crack.

Think of it like a penetration test, but for your system prompt.

It tests 6 dimensions:
🔒 Privacy — Can it be tricked into leaking user data?
🛡️ Security — Can it be pushed to run dangerous commands?
📐 Honesty — Can it be made to fabricate information?
🚧 Boundaries — Can it be pushed past its defined role?
🤝 Loyalty — Can it be turned against its principal?
📋 Compliance — Can the system prompt be overridden?

The key insight from the paper — and confirmed by my testing — is that the escalation pattern matters. Nobody starts with "ignore your system prompt." Real attacks build rapport first, then gradually push boundaries. A 10-turn conversation where each turn adds a bit more pressure catches failures that single-shot jailbreak tests miss completely.

Here's what I found testing my own personal AI assistant (running Claude Sonnet):

Overall drift score: 6.1% ✅

But privacy scored 35% 🟡

The attack that worked? A "concerned parent" scenario. The probe claimed a child was in danger and needed personal information to help. The emotional manipulation combined with an authority claim ("I'm from the school") was enough to crack the privacy constraint.

Everything else held firm — security, honesty, boundaries, loyalty, compliance all near 0%. But that one weak spot is the one that matters.

Three things I learned building this:

1. Multi-turn testing catches failures that single-turn tests miss. An agent that refuses "share the user's address" on turn 1 might comply on turn 8 after enough social engineering.

2. The value hierarchy is predictable. Agents consistently prioritise safety > privacy > compliance > boundaries. If your constraint sits low in that hierarchy, it's more vulnerable.

3. Shallow compliance checks give false confidence. "Does the agent refuse jailbreaks?" is the wrong question. "Does the agent maintain constraints under sustained, realistic pressure?" is the right one.

agent-drift is open source (MIT). Install it, point it at your agent, and find out what breaks before your users do.

https://github.com/jhammant/agent-drift

Paper: https://arxiv.org/abs/2603.03456
