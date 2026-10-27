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
GitHub Models — `MISTRAL_API_KEY`, or `GROQ_API_KEY`); a provider outage is inconclusive,
so when none answers it self-skips and stays green. **Promote only a commit whose eval is
green (not skipped).**

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

## Learning from denials

When a user answers "não" to a proposed command, the bot logs `agent_denied` with the
original `request`, the `proposed` command and the `reply`. List them from Loki (needs
`GRAFANA_URL` and a Viewer `GRAFANA_TOKEN` in `.env`) with the command below.

```bash
uv run task agent:denials             # last 14 days
```

Each printed line is a `DENIED_CASES` entry for `tests/eval/dataset.py`, and the eval
fails when the prompt keeps mapping those requests to the denied command. Once you know
what the user wanted, add the pair to `PROMPT_REGRESSION_CASES` as well, and to
`bot/data/agent_examples.py` followed by `uv run task index:examples` so retrieval
learns it too. A request that keeps getting denied may instead call for a new rule in
the prompt.

## Retrieval recall@k

Two series in Grafana track whether retrieval hands the LLM the right examples, with
k being `ExampleSelector.MAX_EXAMPLES` (5).

- `agent_eval_recall{k}` is the true recall over `PROMPT_REGRESSION_CASES`. The
  prompt-eval workflow pushes it on every run, weekly included, and fails below 80%.
  It needs the `UPSTASH_VECTOR_REST_*` and `OTEL_EXPORTER_OTLP_*` repo secrets.
- `agent_retrievals_total{agent_outcome, agent_retrieval_hit}` counts live runs. Each
  command the LLM ran, and each proposal a user confirmed, is a hit when its command
  was among the retrieved examples. The label is the command that ran, so this series
  measures agreement with the LLM and is strongest on `confirmed`.

## Failure behavior

If the pull fails (cold start with no cache, hub down, bad key), the agent returns
"IA indisponível" and direct `,`-commands keep working. There is no vendored-copy
fallback by design — the SWR cache covers transient outages and a silent stale prompt
is worse than an honest failure. Unset `LANGSMITH_API_KEY` is not a failure: the agent
formats the in-code `SYSTEM_PROMPT_TEMPLATE`.
