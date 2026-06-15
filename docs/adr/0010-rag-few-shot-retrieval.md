---
status: accepted
date: 2026-06-12
---

# 0010 — RAG few-shot retrieval over an example bank

Every agent prompt ships the same `AGENT_EXAMPLES[:20]` slice (`data/agent_examples.py`)
regardless of the user's input. With ~50 commands, many carrying several flags/options, a
well-covered example set is hundreds of phrasings that cannot fit one prompt — the catalog has
outgrown the static slice. Retrieval-augmented few-shot is the fit
([PRD](../prd-agentic-command-mapping.md)), but it must be scoped honestly: naive "RAG for an
LLM bot" would point a vector search at the 46 commands, which already fit the prompt.

## Decision

- **RAG is for the *examples*, not the commands.** Embed the user message, retrieve the **top-k
  most similar few-shot examples**, inject those instead of a fixed slice. The command list
  stays in the prompt whole (it fits).
- **Upstash Vector with server-side embedding.** Upsert raw example strings with the target
  command in metadata; query with the raw user message; Upstash embeds both sides and returns
  top-k. No separate embedding provider, no dimension matching. Free tier: 10K vectors,
  dimension ≤ 1536 — ample for hundreds of short examples.
- **Hybrid authoring.** Generate a baseline from each `CommandConfig` (name + aliases +
  `menu_description` + flags/options expanded into phrasings); hand-augment with the pt-br slang
  (`pauleira`, `chino`, `pacotinho`) that makes few-shot work.
- Behind `ExampleRetrieverPort` — the domain never imports the vector client.

## Considered options

- **Vector search over the 46 commands.** The reflexive "add RAG" move. Rejected: the commands
  already fit the prompt (`get_command_list_with_descriptions`); embedding them to find "the
  relevant ones" solves a non-problem — cargo cult.
- **LlamaIndex over Upstash.** The retrieval-specialist keyword. Rejected: Upstash Vector embeds
  and searches natively (~10 lines with the `upstash-vector` client), so LlamaIndex would be a
  thin wrapper doing little real work while carrying real import weight on the 1 GB core node
  ([ADR 0007](./0007-agent-frameworks-behind-ports.md)). The honest keywords — RAG, vector
  search, vector database — survive without it.
- **All-hand-authored examples.** Highest quality. Rejected: 150–300 manual entries that do not
  scale when a command is added (someone must remember to add examples).
- **All-generated from config.** Zero manual work, scales automatically. Rejected: phrasings
  read robotic (`execute score now`), losing the natural language that makes few-shot work.

## Consequences

- **Index invalidation on change.** Editing an example or adding a command means re-upserting
  the affected vectors; the generated baseline makes this a re-run, not hand-curation.
- **One retrieval call per inbound message** against the Upstash Vector free-tier request cap —
  sporadic command volume keeps it under.
- **No local Upstash emulator.** Retrieval is tested with an in-memory fake behind the port; a
  real Upstash integration test is optional/manual ([ADR 0011](./0011-agent-port-testing.md)).
- **The static `AGENT_EXAMPLES[:20]` slice and `MAX_AGENT_EXAMPLES`** are retired once retrieval
  lands (PRD §9).
