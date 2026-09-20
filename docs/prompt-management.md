# Prompt management runbook

How the agent's system prompt is edited, tested, promoted, and rolled back after it
was decoupled into the LangSmith Prompt Hub ([ADR 0013](./adr/0013-prompt-registry-langsmith.md),
[PRD](./prd-prompt-registry-langsmith.md)).

## Model

- **Source of truth for the seed:** `SYSTEM_PROMPT_TEMPLATE` in
  `bot/data/agent_examples.py`. It is what `scripts/push_prompt.py` publishes and the
  fallback the agent formats when `LANGSMITH_API_KEY` is unset.
- **Registry:** the LangSmith prompt `resenhazord-agent`. Each push is an immutable
  commit; aliases (`dev`, `prod`) are moving pointers to a commit.
- **What the bot serves:** `resenhazord-agent:prod`, pulled at runtime and cached
  stale-while-revalidate (TTL ~5 min). Promoting a new commit to `prod` reaches
  production within that window — **no re-deploy**.
- **What the bot never serves:** `dev`. That alias is the eval target.

## One-time setup

1. Create a LangSmith account (free Developer tier) and an API key.
2. Put `LANGSMITH_API_KEY` in `.env` (and in GitHub repo secrets for the eval workflow).
3. Seed the hub straight to `prod`:
   ```bash
   uv run task prompt:push -- --tag prod
   ```

## Editing the prompt

Two entry points, same promotion path:

- **In the repo:** edit `SYSTEM_PROMPT_TEMPLATE`, then `uv run task prompt:push` (tags `dev`).
- **In the LangSmith playground:** commit there; it lands as a new commit you tag `dev`.

Then evaluate and promote:

```bash
uv run task prompt:push              # publish current template as a `dev` commit
uv run task prompt:eval              # local regression eval (needs provider keys)
uv run task prompt:promote           # re-tag the dev commit as `prod`
```

The `prompt-eval` GitHub workflow runs the same eval automatically on changes to
`bot/data/agent_examples.py`, `tests/eval/**`, or the prompt scripts, and on demand
(`workflow_dispatch`, input `prompt_tag`). It needs a provider secret to do real work
(`GH_MODELS_TOKEN` — a PAT, since the built-in Actions token does not authenticate
GitHub Models — `MISTRAL_API_KEY`, or `GROQ_API_KEY`); with none set it self-skips and
stays green. **Promote only a commit whose eval is green (not skipped).**

## Rollback

Point `prod` back at an older green commit:

```bash
uv run task prompt:promote -- --source <commit-hash>
```

The bot serves it within the cache TTL. No deploy, no revert PR.

## Observability

The agent stamps every mapping with the serving prompt version and outcome, in Grafana:

- Span attributes on `command.handle`: `agent.prompt.version` (the LangSmith commit hash),
  `agent.provider`, `agent.outcome`.
- Counter `agent.mappings{agent.outcome, agent.provider, agent.prompt.version}`.

To investigate a bad-mapping wave: filter `agent.mappings` by `agent.outcome` and split by
`agent.prompt.version` to see whether a prompt version correlates, then roll back.

## Failure behavior

If the pull fails (cold start with no cache, hub down, bad key), the agent returns
"IA indisponível" and direct `,`-commands keep working. There is no vendored-copy
fallback by design — the SWR cache covers transient outages and a silent stale prompt
is worse than an honest failure. Unset `LANGSMITH_API_KEY` is not a failure: the agent
formats the in-code `SYSTEM_PROMPT_TEMPLATE`.
