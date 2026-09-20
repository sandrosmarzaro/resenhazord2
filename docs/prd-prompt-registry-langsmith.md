# PRD — Prompt Registry (decouple the system prompt into LangSmith)

**Status:** Draft · **Date:** 2026-09-20 · **Owner:** Sandro

Decouple the agent's system prompt from the source tree. The prompt moves from a
Python constant into the **LangSmith Prompt Hub**, versioned and pulled at runtime,
so editing the inference rules no longer means a code deploy. Observability of the
mapping stays in the existing OTel → Grafana stack; homologation is a pytest eval
gate in CI. Architecture and rationale: [ADR 0013](./adr/0013-prompt-registry-langsmith.md).

## 1. Problem

The agent's system prompt is `SYSTEM_PROMPT_TEMPLATE` in `bot/data/agent_examples.py`
— a Python string assembled at runtime by `AgentExecutor._build_prompt`. Every change
to the inference rules (a new command's phrasing, an NSFW verb, a sticker-type cue) is
a code change: branch, review, re-deploy of the core node.

- **No independent lifecycle.** The prompt's churn rate and risk profile are nothing
  like the code around it, yet they share a deploy. A one-word tweak waits on CI and a
  container rebuild.
- **No version history or homologation.** There is no record of what the prompt was last
  week, no way to A/B a wording, no gate that proves a change did not regress the mapping
  before it reaches the group.
- **The survey framing.** In prompt-management maturity terms this is "prompts hardcoded
  in source" — the floor. The target is decoupled + versioned + tested + updatable without
  re-deploy.

## 2. Goals

1. **Update without re-deploy.** A prompt edit reaches production by promoting a hub
   version, not by shipping a container — within the SDK cache TTL (~5 min).
2. **Versioned with homologation.** Every prompt is an immutable hub commit; a held-out
   regression eval gates promotion to the alias the bot serves.
3. **Observability stays in Grafana.** No second tracing plane. The serving prompt version
   becomes a span/metric dimension so mappings correlate to the prompt that produced them.
4. **Free and minimal.** LangSmith registry-only keeps the account on the free tier and the
   vendor off the trace hot path; the whole thing gates off when the key is absent.

## 3. Non-goals

- **LangSmith tracing / datasets / playground.** Tracing stays off (quota + second plane);
  eval lives in `tests/eval/`, not a SaaS dataset.
- **Externalizing the few-shot examples or `command_list`.** Those are runtime-injected
  (`command_list` comes from the live registry); only the static instruction template is
  hub-managed.
- **Per-group or per-locale prompts.** One `resenhazord-agent` prompt; variants are out of
  scope.

## 4. Design

| Concern | Choice |
|---|---|
| Registry | LangSmith Prompt Hub, `pull_prompt("resenhazord-agent:prod")`, SWR-cached |
| Seed / fallback | in-code `SYSTEM_PROMPT_TEMPLATE`; used when `LANGSMITH_API_KEY` empty |
| Port | `PromptRegistryPort.system_prompt() -> SystemPrompt(template, version)` |
| Observability | OTel → Grafana: `agent.prompt.version` span attr + `agent.mappings` counter |
| Homologation | `tests/eval/` accuracy gate (`eval` marker) + `prompt-eval` workflow |
| Promotion | `scripts/promote_prompt.py` re-tags an eval-passed commit as `prod` |
| Failure | `PromptRegistryError` → "IA indisponível"; no vendored-copy fallback |

## 5. Operational flow

1. Edit the prompt (repo `SYSTEM_PROMPT_TEMPLATE` or the LangSmith playground).
2. `uv run task prompt:push` → new hub commit tagged `dev`.
3. `prompt-eval` workflow (or `uv run task prompt:eval`) runs the regression eval on `dev`.
4. Green → `uv run task prompt:promote` re-tags that commit `prod`; the bot picks it up on
   its next cached pull. Rollback: promote an older green commit.

Runbook: [docs/prompt-management.md](./prompt-management.md).

## 6. Rollout

- **Phase 1** — registry adapter + port + settings, wired into `AgentExecutor` (done).
- **Phase 0** — `push_prompt` / `promote_prompt` scripts; operator seeds the hub (done).
- **Phase 2** — Grafana instrumentation of the mapping path (done).
- **Phase 3** — eval dataset + `prompt-eval` CI gate (done).
- **Phase 4** — ADR 0013, this PRD, runbook, `.env` (done).

## 7. Risks

- **Free-tier trace cap (5k/mo).** Mitigated by registry-only: tracing stays off, ~0 traces.
- **Cold-start pull failure.** Accepted: SWR cache covers transients; a cold miss with the
  hub down degrades to "IA indisponível", direct commands unaffected.
- **Eval quota.** The eval hits real providers; kept out of the default suite and run only
  on prompt changes / on demand. GitHub Models runs on the built-in Actions token.
- **Second vendor.** A deliberate cost for update-without-deploy; scoped to one cached read
  and gated off without a key.
