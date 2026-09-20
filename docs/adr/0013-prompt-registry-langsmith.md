---
status: accepted
date: 2026-09-20
---

# 0013 — Decouple the agent's system prompt into a LangSmith registry

The agent's system prompt lived as `SYSTEM_PROMPT_TEMPLATE` in
`bot/data/agent_examples.py`. Every wording change to the inference rules was a
code change: commit, review, re-deploy of the core node. The prompt is the
agent's highest-churn, lowest-code-risk surface — it wants a versioned,
independently-updatable home, not a Python string. Four decisions follow.

## Decisions

### 1. LangSmith Prompt Hub as the registry, pulled at runtime

The prompt is pushed to the LangSmith Prompt Hub as an f-string `PromptTemplate`
and pulled at runtime with `Client.pull_prompt("resenhazord-agent:prod")`
(`bot/infrastructure/llm/langsmith_prompt_registry.py`). The SDK caches pulls
stale-while-revalidate (TTL 300s, background refresh 60s), so a hub edit reaches
production within minutes **without a re-deploy** — the property that separates
this from "prompts in an external file the deploy still ships".

The in-code `SYSTEM_PROMPT_TEMPLATE` stays as the seed that `scripts/push_prompt.py`
pushes, and as the default when `LANGSMITH_API_KEY` is empty — the same
config-gates-the-adapter pattern as OTel (empty endpoint) and Sentry (empty DSN).
The registry sits behind `PromptRegistryPort`, consistent with the
agent-frameworks-behind-ports discipline ([ADR 0007](./0007-agent-frameworks-behind-ports.md)).

### 2. Registry-only — observability stays in Grafana, not LangSmith

LangSmith is a tracing platform first; we use **only** its prompt registry.
Tracing stays off (`LANGSMITH_TRACING` unset), so the account generates ~0 traces
and never leaves the free Developer tier (5k traces/mo, 1 seat, Prompt Hub
included). LLM/tool-call observability continues through the existing OTel → Grafana
pipeline (the observability PRD), where the agent now stamps the serving prompt
version (`agent.prompt.version`, its LangSmith commit hash) onto its span and an
`agent.mappings` counter — so a bad-mapping wave can be tied to the exact prompt
version that produced it, without a second observability plane.

A second vendor in the request hot path is a real cost against the minimalist
default. It buys update-without-deploy and a version history that a git-tracked
file cannot (git puts us back to "deploy to change the prompt" — option 3, not 4).
The registry-only scoping keeps the cost to one cached network read, gated off
when the key is absent.

### 3. Homologation is a pytest eval gate in the repo, not a LangSmith dataset

Regression testing of the natural-language → command mapping lives in `tests/eval/`
as a held-out `(request, command-prefix)` dataset run through the real providers,
asserting aggregate accuracy (`eval` marker, excluded from the default suite). The
`prompt-eval` workflow runs it on prompt/eval changes and on demand; a green run
gates `scripts/promote_prompt.py`, which re-tags the evaluated commit as `prod`.

This keeps regression tooling and the approval trail **in the repo and CI** rather
than a SaaS dataset UI — closer to the project's pytest-first testing culture, and
the "integration with repositories, regression tooling, approval pipelines" that a
mature prompt-management setup implies. We trade LangSmith's visual eval/playground
loop for versioned tests and a CI gate.

### 4. Failure degrades, it does not fall back to a vendored copy

A pull failure (cold start with no cache, hub down) raises `PromptRegistryError`,
caught in `AgentExecutor.run` alongside provider failures → the user gets "IA
indisponível" and direct `,`-commands keep working. We deliberately do **not**
ship a stale vendored prompt on failure: the SWR cache covers transient outages,
and a silent stale prompt is worse than an honest "unavailable". This is the
accepted risk of the "trust the cache" fallback stance.

## Consequences

- Prompt edits ship via `prompt:push` → `prompt:eval` (or the workflow) →
  `prompt:promote`, no core re-deploy. Rollback is `prompt:promote` at an older
  green commit. Runbook: [docs/prompt-management.md](../prompt-management.md).
- New secrets for the eval workflow: `LANGSMITH_API_KEY` (optional `MISTRAL_API_KEY`,
  `GROQ_API_KEY`); GitHub Models runs on the built-in token (`models: read`).
- No queue contract changes, so no expand/contract concern
  ([ADR 0006](./0006-two-node-cicd-deploy.md)) — the pull is a read-only,
  node-local call on the core node.
