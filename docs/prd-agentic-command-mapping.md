# PRD — Agentic Command Mapping (stateful NL → command)

**Status:** Draft · **Date:** 2026-06-12 · **Owner:** Sandro

Turn the natural-language command mapper (`bot/application/agent_executor.py`) from a
**stateless single-shot** translator into a **stateful, multi-turn agent**: it retrieves
similar examples (RAG), decides via structured tool calling, executes confidently or
asks back, and remembers the disambiguation across turns. The orchestration moves onto
LangGraph + LangChain, kept **behind ports** so the domain never imports a framework.

## 1. Problem

Today a `@`-mention (groups) or any DM routes the message to `AgentExecutor.run()`, which
builds one prompt and maps it to a command in a single shot. It works, but it is thin:

- **Stateless.** Every `run()` is a fresh prompt. The *only* context is `data.quoted_text`
  (one quoted message). When the agent replies `CLARIFY: você quis dizer X?` and the user
  answers "sim", the next message re-runs the mapper **blind** — the prior question is gone.
  There is no conversation, no memory, no iteration. "Iterar entre dúvidas e opções" — the
  stated product goal — is impossible on this shape.
- **Brittle decision representation.** The agent's three outcomes (execute / clarify /
  suggest) are encoded as free-text markers parsed with `content.startswith(LLM_CLARIFY_MARKER)`
  (`agent_executor.py:72-87`). One missing prefix from the model and the branch collapses to
  the unresolvable fallback.
- **Static, input-blind examples.** Every prompt ships the same `AGENT_EXAMPLES[:20]` slice
  (`data/agent_examples.py`) regardless of what the user asked. With ~50 commands, many with
  several flags/options, the well-covered example space is hundreds of phrasings that cannot
  fit a prompt — so the catalog has outgrown the static slice.
- **A dead provider leg.** `.env.example` advertises a `google` fallback and ships
  `GEMINI_API_KEY`, but there is **no `GoogleProvider`** in `ProviderChain`. Configured,
  never wired.

## 2. Goals

1. **Multi-turn disambiguation with memory.** The clarify → suggest → confirm loop survives
   across inbound messages: the agent remembers it asked X and what the user already answered.
2. **Robust decision representation.** Replace string-marker parsing with **tool calling as
   structured output** — the model's choice is a typed call, not a parsed prefix.
3. **Retrieval-scaled mapping.** Pull the *top-k most similar* few-shot examples per query
   instead of a fixed slice, so mapping quality scales with the catalog (RAG).
4. **Learning vehicle, honestly.** A real agent stack — LangGraph (orchestration), LangChain
   (model + fallback), RAG over a vector database, structured tool calling — each earning its
   place and isolated behind a port, so the keywords are genuine, not decorative
   ([ADR 0007](./adr/0007-agent-frameworks-behind-ports.md)).

## 3. Non-goals

- **No long-term user memory.** Only short-lived conversation state. Cross-session
  personalization (preferences, command history) is a documented future extension (§11),
  not built — its real payoff is résumé, its cost is user PII at rest.
- **No MCP server in v1.** Exposing `CommandRegistry` as a fourth adapter for external MCP
  clients is a clean future extension (§11), tangential to making the agent smarter.
- **No change to the command surface, `CommandRegistry`, or any `Command` subclass.** Only
  the agent orchestration boundary moves — mirrors the broker PRD's discipline.
- **The manual comma-command path is untouched.** This is the *agent* path (`@`-mention /
  DM) only. `,menu` typed directly still parses as today.
- **No LlamaIndex.** Considered and rejected: Upstash Vector embeds and searches natively, so
  LlamaIndex would be a thin wrapper carrying real import weight on the 1 GB core node
  ([ADR 0010](./adr/0010-rag-few-shot-retrieval.md)).

## 4. Current architecture

```
@mention / DM ──▶ AgentExecutor.run(data)
                    │  _build_prompt: SYSTEM_PROMPT_TEMPLATE
                    │    + command list + AGENT_EXAMPLES[:20] (static)
                    │    + data.text + data.quoted_text (one message)
                    ▼
                  ProviderChain.complete(prompt, tools)   github → mistral → groq
                    │  (raw httpx, OpenAI-compatible, 60s cooldown on 429)
                    ▼
                  response.tool_call?  ──▶ translate → ,command args → execute
                  content "CLARIFY: …"  ──▶ reply question  (no state kept)
                  content "SUGGEST: …"  ──▶ reply suggestion (no state kept)
                  else                  ──▶ unresolvable fallback
```

Tool calling and provider fallback are **already real**. The gaps are state (none),
decision robustness (string markers), and example relevance (static slice).

## 5. Proposed architecture

The mapper becomes a **LangGraph state machine** behind `AgentOrchestratorPort`. Three
nodes, a persisted state object, two supporting ports.

```
                         AgentOrchestratorPort  (impl: LangGraph)
   ┌──────────────────────────────────────────────────────────────────────┐
   │  inbound CommandData (+ resumed conversation state, if any)            │
   │      │                                                                 │
   │      ▼                                                                 │
   │   [retrieve] ── ExampleRetrieverPort (impl: upstash-vector) ──────────┐│
   │      │          embed query · top-k similar examples                  ││
   │      ▼                                                                 ││
   │   [decide]  ── LLMProviderPort (impl: LangChain init_chat_model       ││
   │      │            + with_fallbacks) · tool calling = structured output ││
   │      │          → command tool call | clarify(question,conf)           ││
   │      │            | suggest(message,command,conf)                      ││
   │      ▼                                                                 ││
   │   route on (action, confidence):                                      ││
   │      ├─ execute  (high conf) ─▶ CommandRegistry → reply               ││
   │      ├─ clarify / low conf   ─▶ ask, persist state, await next turn    ││
   │      └─ suggest              ─▶ conversational reply + command         ││
   └──────────────────────────────────────────────────────────────────────┘
              state persisted via checkpointer → Upstash Redis
```

| Port | Impl | Responsibility |
|---|---|---|
| `AgentOrchestratorPort` | LangGraph | graph topology, state, checkpointer, routing |
| `LLMProviderPort` | LangChain `init_chat_model().with_fallbacks([...])` | one chat call with fallback; replaces `ProviderChain` |
| `ExampleRetrieverPort` | `upstash-vector` client | embed query, return top-k examples |

The domain (`AgentExecutor`, the ~50 `Command` subclasses, `CommandRegistry`) imports
**only these three interfaces**. No `import langchain` / `langgraph` / `upstash_vector`
crosses into `bot/domain` or `bot/application`. That boundary is what makes a three-keyword
stack defensible rather than cargo cult ([ADR 0007](./adr/0007-agent-frameworks-behind-ports.md)).

### Decision as tool calling

The `decide` node does not parse prefixes. The model is given the **command tools** (the
existing `command_to_tool_schema` output) plus two **meta-tools**:

- `clarify(question: str, confidence: float)`
- `suggest(message: str, command: str, confidence: float)`

A command tool call *is* the `execute` action; the meta-tools carry the other two outcomes.
`confidence` is a tool argument. Routing is a `switch` over the called tool, never a
`.startswith()` over text. Tool calling is OpenAI-compatible across github/mistral/groq, so
this rides the providers already in use; the `LLMProviderPort` normalizes provider variance
([ADR 0009](./adr/0009-confidence-gated-execution.md)).

## 6. Conversation state

Short-term only. The clarify/confirm loop needs to remember, across **separate inbound
messages**, that a question is open and what was already answered. Full rationale in
[ADR 0008](./adr/0008-conversation-state-and-resume.md).

- **LangGraph checkpointer persisted to Upstash Redis** (already in the stack), not the
  in-memory `MemorySaver`. The bot is the frequently-redeployed side (broker PRD Goal 2) and
  the `commands` queue allows future competing consumers — in-memory state dies on every
  redeploy and is invisible to a second worker. Redis survives both.
- **Thread identity `plataforma:chat:user`.** Two users disambiguating in the same group must
  not collide; one user in two chats must not cross-talk.
- **Hybrid resume — quote wins, else a short window.** The loop resumes if the user *quotes*
  the bot's question (uses `quoted_message_id`, already in `CommandData`) **or** sends free
  text within ~60–90 s. Quote takes precedence. This kills the "sim" ghost (a stray yes an
  hour later resurrecting dead state) while keeping the natural no-quote answer working inside
  the window.

## 7. RAG few-shot retrieval

Replace the static `AGENT_EXAMPLES[:20]` slice with retrieval. Full rationale in
[ADR 0010](./adr/0010-rag-few-shot-retrieval.md).

- **RAG is for the examples, not the commands.** All ~50 commands already fit the prompt;
  embedding them to "find the relevant ones" solves a non-problem. What scales past the prompt
  is the *example bank* (~150–300 phrasings covering commands × flags/options).
- **Upstash Vector with server-side embedding.** Upsert raw example strings with the target
  command in metadata; query with the raw user message; Upstash embeds both sides and returns
  top-k by similarity. **No separate embedding provider, no dimension matching.** Free tier:
  10K vectors, dimension ≤ 1536 — ample for hundreds of short examples.
- **Hybrid authoring.** A generated baseline from each `CommandConfig` (name + aliases +
  `menu_description` + flags/options expanded into phrasings) gives automatic coverage that
  scales with the catalog; hand-augmentation adds the pt-br slang (`pauleira`, `chino`,
  `pacotinho`) that makes few-shot actually work.

## 8. Reliability, free-tier, idempotency

- **Provider fallback moves into LangChain.** `init_chat_model().with_fallbacks([...])`
  replaces the hand-rolled `ProviderChain` rotation. This is a *lateral* swap — `ProviderChain`
  already does fallback + 429 cooldown well — justified by consolidating onto one stack and
  inheriting streaming/retries/observability, not by new capability
  ([ADR 0007](./adr/0007-agent-frameworks-behind-ports.md)). The dead `google`/Gemini leg is
  either wired here as a real LangChain provider or removed from `.env.example`.
- **Free-tier ceilings are real.** Groq free is ~30 RPM / ~1 000 req/day on
  `llama-3.3-70b-versatile`. Multi-turn multiplies LLM calls per interaction, but
  confidence-gating keeps the common case at one call, and the fallback chain sums several
  providers' daily quotas. Upstash Vector and Upstash Redis free tiers cap requests/day too —
  retrieval is one call per inbound message, checkpoint reads/writes one per turn.
- **At-least-once redelivery (broker [ADR 0001](./adr/0001-at-least-once-delivery.md)) meets
  stateful graph.** The agent runs inside the command consumer, so a redelivered inbound
  message could re-run a graph turn. `decide` is a pure function of (state, input): re-running
  yields the same routing and the executed command inherits ADR 0001's replay-safety. The only
  residual is a duplicate turn appended to conversation history — bounded by the crash gap,
  cosmetic, not corrupting. If it ever matters, gate graph progression on the existing
  `message_id` idempotency key (the ADR 0001 escape hatch), not before.

## 9. Migration phases

Each ships independently behind a flag, parallel-run with the current `AgentExecutor` until
the last. Mirrors the broker PRD: ports + test seam first so every later phase has both test
layers from the start ([ADR 0011](./adr/0011-agent-port-testing.md)).

1. **Ports + test seam.** Define `AgentOrchestratorPort`, `LLMProviderPort`,
   `ExampleRetrieverPort`. Wire the conftest `_reset_singletons` fixture, a `fakeredis`
   checkpointer harness, and an in-memory `ExampleRetrieverPort` fake. No behavior moves yet.
2. **`LLMProviderPort` over LangChain.** Wrap `init_chat_model` + `with_fallbacks` behind the
   port, parallel to `ProviderChain` behind a flag. Retire `ProviderChain` once proven.
3. **`ExampleRetrieverPort` + RAG.** Build the example bank (generated + augmented), index to
   Upstash Vector, swap the static `[:20]` slice for retrieved top-k. Lowest-risk visible
   improvement; no state involved yet.
4. **`AgentOrchestratorPort` graph.** LangGraph `retrieve → decide → route` with tool-calling
   decision and confidence gating. Replaces the hand-rolled `run()` if/elif. Still single-turn.
5. **Conversation state.** Add the Redis checkpointer, `thread_id`, and hybrid resume. This is
   the turn that unlocks multi-turn iteration.
6. **Cleanup.** Delete the marker constants (`LLM_CLARIFY_MARKER`/`LLM_SUGGEST_MARKER`) and the
   string-parse branch; resolve the dead Gemini leg. Update `docs/architecture.md`.

Each phase: tests alongside (pytest), commit atomically, verify before the next.

## 10. Risks

- **Memory on the 1 GB core node.** LangGraph + LangChain add real import footprint to a bot
  already at 150–360 MB (`project-vps-cpu-runaway`). LlamaIndex was dropped partly for this.
  Mitigations: these are the only heavy adds, lazy imports where possible, per-container
  `mem_limit`, monitor RSS after phase 4.
- **Free-tier rate limits under multi-turn.** §8. Bounded by confidence-gating + fallback sum;
  surface 429 exhaustion to Sentry.
- **Structured-output reliability varies by provider.** Tool-calling adherence differs across
  github/mistral/groq. The `LLMProviderPort` normalizes and the fallback chain covers a
  provider that returns malformed/no tool call; a final unresolvable fallback remains.
- **`xenon --max-absolute B` complexity gate.** Graph routing can sprawl. Keep each node small
  and single-purpose; the gate enforces it.
- **No local Upstash emulator.** Unlike RabbitMQ (testcontainers), Upstash Vector/Redis have no
  container. Retrieval is tested with an in-memory fake behind the port; the checkpointer with
  `fakeredis` ([ADR 0011](./adr/0011-agent-port-testing.md)).

## 11. Future extensions (documented, not built)

- **Long-term user memory.** A per-user store (preferences, command history) retrieved to
  personalize. Deferred for PII-at-rest cost and thin UX payoff; revisit if personalization
  becomes a real ask.
- **MCP as a fourth adapter.** A server exposing `CommandRegistry` to external MCP clients,
  reusing `command_to_tool_schema` — MCP alongside WhatsApp/Discord/Telegram, all on the same
  registry. Built when a real MCP consumer appears.

## 12. Observability

Reuse the broker PRD's correlation id (§12): every inbound message carries
`CommandData.message_id`. Bind it into `structlog` contextvars and the Sentry scope on each
node, **plus `thread_id`** so a multi-turn conversation — which spans several inbound messages
— is greppable as one thread. A non-resolving spike (rising unresolvable fallbacks) and
free-tier 429 exhaustion are the signals worth alerting on. Full OpenTelemetry tracing stays
out of scope, same reasoning as the broker PRD.

## 13. Testing strategy

TDD (RED → GREEN → REFACTOR); testability is a design constraint. Full rationale in
[ADR 0011](./adr/0011-agent-port-testing.md).

- **Unit — mock the three ports.** Canned structured decisions (`LLMProviderPort`), canned
  retrieved examples (`ExampleRetrieverPort`). Graph routing, confidence gating, resume logic,
  and translation are exercised deterministically. Never mock LangChain/LangGraph internals —
  *don't mock what you don't own*.
- **Conversation state — `fakeredis`** (already a dep). The checkpointer round-trip, thread
  keying, and resume window are tested locally with no cloud.
- **Retriever — in-memory fake.** No Upstash container exists; the port's fake returns
  deterministic top-k. A real Upstash integration test is optional/manual, secret-gated.
- **Timing discipline.** Resume-window tests use short TTLs + event-or-poll waits, never
  `asyncio.sleep` (a `testing.md` rule).
