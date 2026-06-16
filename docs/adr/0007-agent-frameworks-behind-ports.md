---
status: accepted
date: 2026-06-12
---

# 0007 — Agent frameworks behind ports (LangGraph + LangChain)

Turning the stateless NL→command mapper into a stateful multi-turn agent
([PRD](../prd-agentic-command-mapping.md)) needs orchestration with persisted state and a
provider layer with fallback. Two frameworks fit: **LangGraph** for the graph/state machine,
**LangChain** for the chat model + fallback. Both carry the well-known cost of framework
churn and leaky abstractions, and both add import weight to a 1 GB core node already at
150–360 MB. The project is also a résumé vehicle where these are deliberately-targeted
keywords. The tension is real: keyword breadth versus the minimalism that keeps a bot robust.

## Decision

**Adopt LangGraph + LangChain, each isolated behind a port the domain owns** — mirroring the
existing `WhatsAppPort` / `BrokerPort` / `AxiosClient` seams.

- `AgentOrchestratorPort` → LangGraph: graph topology, state object, checkpointer, routing.
- `LLMProviderPort` → LangChain `init_chat_model().with_fallbacks([...])`: one chat call with
  provider fallback. **Replaces the hand-rolled `ProviderChain`.**

No `import langchain` / `import langgraph` crosses into `bot/domain` or `bot/application`. The
~50 `Command` subclasses, `CommandRegistry`, and `AgentExecutor` talk only to the interfaces.

The senior signal here is **not** "imported two frameworks" — it is "isolated two volatile
frameworks behind my own boundaries, so either can be torn out without touching the domain."
The framework choice is reversible; that is what makes the keyword choice defensible.

## Considered options

- **Raw clients, no framework** (keep `httpx` + hand-rolled state). Most minimalist, zero new
  heavy deps, and `ProviderChain` already does fallback + 429 cooldown well. Rejected: it
  yields zero of the stated résumé keywords and a hand-rolled checkpointer/graph for multi-turn
  is reinventing exactly what LangGraph is.
- **LangChain only, no LangGraph** (linear chains + memory classes). Lighter, one ecosystem.
  Rejected: the clarify → confirm → execute loop *is* a state machine; modeling it as a graph
  with an explicit persisted state is the honest fit, and LangGraph is the more
  production-respected of the two.
- **Triad with LlamaIndex** for retrieval. Rejected — Upstash Vector embeds and searches
  natively, so LlamaIndex would be a thin wrapper carrying real import weight on the 1 GB node
  ([ADR 0010](./0010-rag-few-shot-retrieval.md)).

## Consequences

- **The `LLMProviderPort` ← `ProviderChain` swap is lateral, not vertical.** It abandons clean
  working code for a framework that does the same job, gaining the keyword and inheriting
  streaming/retries/observability — not new capability. Stated plainly so the trade is honest.
- **Memory footprint grows on the 1 GB core node.** These two are the only heavy adds (the
  third candidate, LlamaIndex, was dropped). Lazy imports, per-container `mem_limit`, and an
  RSS check after the graph lands (PRD §10) contain it.
- **One new abstraction pair** — but it pattern-matches `WhatsAppPort` / `BrokerPort`, so it is
  consistency, not net-new surface (CLAUDE.md: match existing patterns first).
- **The `xenon --max-absolute B` gate** forces graph nodes to stay small and single-purpose.
