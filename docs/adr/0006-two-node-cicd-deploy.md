---
status: accepted
date: 2026-06-08
---

# 0006 — CI/CD deploy for the two-node topology

The two-node split ([ADR 0002](./0002-two-node-topology.md)) breaks the single-host
deploy assumption baked into `pipeline.yml`, whose one `deploy` job SSHes to a single
`VPS_HOST` and runs `git pull && docker compose pull && docker compose up -d`. Three
decisions follow.

## Decisions

### 1. Two explicit deploy jobs, not a matrix

`deploy-edge` and `deploy-core`, each SSHing to its own host and running its own compose
file (`compose.edge.yml` / `compose.core.yml`). New per-node secrets
(`VPS_EDGE_HOST` / `VPS_CORE_HOST`, …) replace the single `VPS_HOST`. Downstream jobs
become `needs: [deploy-edge, deploy-core]`.

A matrix over `[edge, core]` would be DRY-er and make a third node a one-liner, but
there are only **two** nodes — "tolerate duplication until the third occurrence". Two
explicit jobs read obviously and add no expression cleverness (dynamic `secrets[...]`
indexing). Revisit the matrix if a third node (a scale-out worker) ever lands.

### 2. The non-atomic deploy is handled by contract discipline, not orchestration

Gateway (VM-A) and bot (VM-B) deploy independently, so a release that changes the queue
*contract* (routing key, payload schema, binding) has a window where one node speaks the
new dialect and the other the old. Rather than orchestrate (ordered deploy, maintenance
window), **queue-contract changes are expand/contract**: ship the additive half first
(new queue/field/binding coexisting with the old), migrate consumers, drop the old in a
later release. Then deploy order never matters and both jobs run in parallel. This is a
**guard rule** (sibling to [ADR 0001](./0001-at-least-once-delivery.md)'s idempotency
rule) for `.claude/rules/git.md`, scope `.github/**` — not built machinery.

`docker compose up -d` is declarative, so a code-only deploy recreates only the changed
container; **RabbitMQ on the edge node stays up across gateway deploys** and the bot
barely notices. A code-only deploy (no contract change) is fully covered by reconnect +
at-least-once + graceful drain (§7).

### 3. Split the nodes first (phase 1), not last

VM-B is provisioned and the bot moved to it **at the start** of the migration, so the
rollout never runs `rabbitmq` + gateway + bot on one 1 GB box — the §9 OOM risk, on the
box that already froze once, is designed out from the start.

## Considered options

- **Ordered deploy + drain / maintenance window** (for the skew window). Rejected —
  orchestration the expand/contract discipline makes unnecessary; a maintenance window
  also violates Goal 2 (decoupled lifecycles).
- **Matrix deploy.** Rejected for two nodes (see decision 1).
- **Migrate WS→AMQP on the single host, split last.** Rejected — it runs three
  processes on 1 GB through phases 1–5, exactly the OOM the split exists to prevent.

## Consequences

- The still-live WS path crosses VMs during the phase-3 parallel-run (was localhost), so
  the `/ws` port is exposed on the VCN private subnet temporarily — plumbing for a path
  phase 5 deletes, accepted as the price of avoiding OOM.
- Each VM keeps its own `.env`; the cross-service `depends_on` disappears (broker
  durability replaces boot ordering).
- `pipeline.yml`'s `register-deploy`, `tag`, and `back-merge` jobs re-point their
  `needs` to both deploy jobs.
