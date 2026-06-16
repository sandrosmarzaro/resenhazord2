---
status: accepted
date: 2026-06-12
---

# 0009 — Confidence-gated execution + tool calling as structured decision

The agent has three outcomes — execute a command, ask to clarify, suggest a similar command.
Today they are free-text markers parsed with `content.startswith(LLM_CLARIFY_MARKER)`
(`agent_executor.py:72-87`): one missing prefix collapses the branch to the unresolvable
fallback. Separately, the agent maps and **executes in one shot** with no confirmation — fine
for the obvious case, wrong when the mapping is a guess. Two decisions, coupled in the `decide`
node ([PRD](../prd-agentic-command-mapping.md)).

## Decision

**Represent the decision as tool calling.** The model receives the existing command tools
(`command_to_tool_schema`) plus two meta-tools:

- `clarify(question: str, confidence: float)`
- `suggest(message: str, command: str, confidence: float)`

A command tool call *is* the `execute` action; the meta-tools carry the other two. Routing is a
`switch` over the called tool, never a `.startswith()` over text.

**Gate execution on confidence.** High confidence → execute directly (no friction on `,carro`).
Below a threshold → route to clarify/confirm before running. The threshold is a named,
tunable constant.

## Considered options

- **Keep free-text markers.** Zero change. Rejected: it is the brittleness this PRD exists to
  remove; the model silently dropping a prefix is a whole bug class.
- **JSON mode / `response_format` for a decision object.** Also structured. Rejected as the
  primary mechanism: tool-calling adherence is more uniform across the OpenAI-compatible
  providers in use (github/mistral/groq) than JSON-mode support, and the command tools already
  exist — reusing them is one mechanism, not two.
- **Always execute, correct after (no gate).** Minimal friction. Rejected: it executes wrong
  commands (sends wrong media, burns an API call), and memory only helps *after* the mistake.
- **Always confirm before execute.** Maximum safety/interaction. Rejected: confirming `,menu`
  and `,carro` every time exhausts the user fast, and every extra turn is another LLM call
  against a ~1 000 req/day free ceiling.

## Consequences

- **The threshold needs calibration** and trusts the model's self-reported confidence — a soft
  signal. Start conservative (execute only when clearly high), widen with observed behavior.
- **Provider variance in tool-calling adherence** is normalized at `LLMProviderPort`; a provider
  returning a malformed or absent tool call falls through the chain, with a final unresolvable
  fallback preserved.
- **Confidence-gating bounds the free-tier cost** of multi-turn: the common case stays at one
  call, extra turns happen only on genuine ambiguity.
- **Cleanup:** `LLM_CLARIFY_MARKER` / `LLM_SUGGEST_MARKER` and the string-parse branch are
  deleted in the final migration phase (PRD §9).
