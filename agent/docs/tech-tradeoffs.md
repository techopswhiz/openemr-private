# OpenEMR Agent — Technology Tradeoffs Reference

## LLM: xAI Grok 3 Mini Fast (OpenAI-compatible API)

**Alternatives considered:** GPT-4o, Claude, local open-source models

| Pro | Con |
|-----|-----|
| Very fast inference (the "fast" variant) | Less capable than GPT-4/Claude for complex reasoning |
| Low cost — important for a sidecar running many queries | Less proven in clinical/medical NLP |
| OpenAI-compatible API = easy provider swap (one config change) | No local/on-prem option — PHI leaves network |
| `temperature=0` for deterministic clinical outputs | Dependent on xAI pricing/availability |

**Key decision:** `ChatOpenAI` with custom `base_url` makes switching providers a config change, not a code change.

---

## Orchestration: LangGraph

**Alternatives considered:** Raw LangChain agents, custom state machine, CrewAI

| Pro | Con |
|-----|-----|
| Explicit graph — easy to reason about agent flow | Heavier than a simple while loop |
| Built-in `ToolNode` + `tools_condition` reduce boilerplate | API still evolving (potential breaking changes) |
| Clean separation of verify/format as graph nodes | Currently overkill for a linear ReAct loop |
| Native LangSmith tracing integration | |

**Graph structure:** `START -> agent -> [tools loop] -> verify -> format -> END`

Simple enough for a plain loop today, but scales for parallel tool calls or branching later.

---

## HTTP Framework: FastAPI + Uvicorn

**Alternatives considered:** Flask, Django, raw ASGI

| Pro | Con |
|-----|-----|
| Native async/await — critical for I/O-bound agent (LLM + API calls) | Async-only means sync libraries need wrapping |
| Auto-generated OpenAPI docs | Lighter than Django (no ORM, admin) |
| Pydantic validation for request/response models | |
| Uvicorn is production-ready ASGI server | |

**Why it matters:** Every request hits 2-3 external services (xAI, OpenEMR, NLM). Async is the right paradigm.

---

## HTTP Client: httpx (async)

**Alternatives considered:** aiohttp, requests

| Pro | Con |
|-----|-----|
| Async-native, pairs with FastAPI | `verify=False` disables TLS — security gap in prod |
| Clean API, similar to `requests` | |
| Built-in timeout + retry support | |

**Production gap:** `verify=False` is pragmatic for self-signed dev certs but needs proper TLS certs in production.

---

## Observability: LangSmith + Custom Metrics

**Alternatives considered:** OpenTelemetry, Datadog, Langfuse

| Pro | Con |
|-----|-----|
| Zero-config with LangGraph (just env vars) | Proprietary SaaS — vendor lock-in |
| Auto-traces every LLM call, tool call, token count | Costs scale with usage |
| Built-in feedback API for human eval | Less flexible than OTel for non-LLM metrics |

**Dual tracking pattern:** LangSmith handles LLM traces; custom `metrics.py` covers HTTP latency, tool timing, error counts. They complement each other.

---

## Verification: Rule-Based Post-Processing

**Alternatives considered:** LLM-as-judge, no verification

| Pro | Con |
|-----|-----|
| Deterministic — no extra LLM call, zero added cost/latency | Limited to pattern matching |
| Binary pass/fail aligns with Gauntlet eval framework | Can't catch subtle clinical reasoning errors |
| Covers the 3 most dangerous failure modes | Hardcoded risky phrases are brittle |

**Three verification types:**
1. **Interaction severity** — flags HIGH/MODERATE drug interactions from tool results
2. **Allergy conflict** — flags allergy-drug cross-check conflicts
3. **Prescriptive language** — keyword scan for phrases like "you should take", "discontinue"

Right call for MVP. LLM judges are expensive, non-deterministic, and the assignment requires binary checks.

---

## Auth: OAuth2 Password Grant

**Alternatives considered:** Client Credentials, SMART on FHIR launch, API keys

| Pro | Con |
|-----|-----|
| Simple — one token request, no browser redirect | Password grant deprecated in OAuth 2.1 |
| Works for server-side sidecar (no browser user) | Stores username/password in env vars |
| Token caching with expiry buffer + auto-refresh on 401 | Not suitable for multi-tenant/multi-user |

**Production path:** For multi-user, would need SMART on FHIR launch sequences (significantly more complex).

---

## Summary

The stack optimizes for **speed-to-MVP** and **swappability**:

- xAI model behind OpenAI-compatible interface = easy swap
- LangGraph slightly over-engineered for current flow but positions for future complexity
- Rule-based verification avoids LLM judge costs while catching critical clinical safety issues
- **Biggest production gaps:** `verify=False` on TLS, password grant auth model
