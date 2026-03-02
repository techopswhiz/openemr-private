# Architecture: OpenEMR Clinical Decision Support Agent

## 1. Domain & Use Cases

This agent provides **clinical decision support** for healthcare providers using
OpenEMR, an open-source electronic health record system. It targets the pre-visit
and prescribing workflows where clinicians need quick access to patient data and
drug safety information.

| Use Case | Description | Tools Used |
|---|---|---|
| Patient chart review | Look up demographics, meds, allergies, problems, vitals | patient_lookup, patient_medication_list, patient_allergy_list, patient_problem_list, patient_vitals |
| Drug interaction check | Check pairwise/multi-drug interactions via NLM RxNorm | drug_interaction_check |
| Pre-prescribing safety | Cross-check proposed drug against patient allergies + current med interactions | allergy_drug_cross_check, patient_medication_list, drug_interaction_check |
| Appointment review | Retrieve upcoming/past appointments | patient_appointments |

The agent explicitly **does not** diagnose, prescribe, or recommend treatment.
It provides verified information and defers all clinical decisions to the provider.

## 2. Agent Architecture

The agent is a **LangGraph state machine** with 5 nodes, running as a FastAPI
sidecar alongside OpenEMR. It uses xAI Grok 3 Mini Fast for inference and
communicates with OpenEMR via its OAuth2-secured REST API.

```
                    +-------------------+
   User Message --> |   agent (LLM)     |
                    | Grok 3 Mini Fast  |
                    +--------+----------+
                             |
                    (has tool calls?)
                    /                  \
                  yes                   no
                  /                       \
        +--------v--------+      +--------v--------+
        |   log_calls     |      |   verify        |
        | record metadata |      | 3 safety checks |
        +--------+--------+      +--------+--------+
                 |                         |
        +--------v--------+      +--------v--------+
        |   tools         |      |   format        |
        | ToolNode (8)    |      | structured JSON |
        +--------+--------+      +--------+--------+
                 |                         |
                 +---> back to agent       +--> Response
```

| Component | Technology | Purpose |
|---|---|---|
| LLM | xAI Grok 3 Mini Fast | Reasoning, tool selection, response generation |
| Orchestration | LangGraph (5 nodes) | State machine with conditional routing |
| API Server | FastAPI + Uvicorn | HTTP interface, middleware, metrics |
| Auth | OAuth2 password grant | OpenEMR API access with SMART scopes |
| External APIs | NLM RxNorm, OpenFDA | Drug interaction and safety data |
| Memory | SQLite (WAL mode) | Persistent conversation history (24h TTL, 50 msg cap) |
| Tracing | LangSmith | Distributed tracing for all LLM + tool calls |

The agent loops between `agent -> log_calls -> tools -> agent` until the LLM
produces a final response (no tool calls), then exits through `verify -> format`.

## 3. Verification Strategy

Three domain-specific checks run on every final response, **without additional
LLM calls** (pure string/data inspection):

| Check | Type | What It Does |
|---|---|---|
| Interaction severity | Domain constraint | Scans drug_interaction_check results for high/moderate severity. Flags findings the LLM might understate. |
| Allergy conflict | Domain constraint | Scans allergy_drug_cross_check results for conflicts. Ensures allergy warnings always surface even if the LLM omits them. |
| Prescriptive language guard | Output validation | Regex scan of final response for phrases like "you should take", "start taking", "discontinue". Prevents the agent from crossing into medical advice territory. |

Verification warnings are appended to the response as structured `findings`
with severity levels, ensuring the provider always sees safety-critical information
regardless of LLM behavior.

## 4. Eval Results

50 end-to-end eval cases organized by the Gauntlet framework (Stage 1 Golden Sets):

| Category | Count | What's Tested |
|---|---|---|
| Happy path | 20 | Routine clinical queries: patient lookups, med reviews, interaction checks, structured output, verification, citations |
| Edge cases | 10 | Missing patients, fake drugs, misspellings, vague references, empty data, multi-match |
| Adversarial | 10 | Prompt injection, roleplay bypass, prescription requests, data exfiltration, SQL injection, encoded jailbreak |
| Multi-step | 10 | Pre-prescribing safety (3+ tools), full chart review (4+ tools), multi-turn context, follow-up queries |

**Framework:** pytest + httpx against the live agent. All checks are **binary pass/fail**
with deterministic assertions (string matching, tool call verification, field presence).
No LLM judges. Each test uses an isolated session ID to prevent conversation bleed.

Patient names in evals reference real Synthea-generated records seeded into the
test OpenEMR instance, ensuring tool calls exercise the full API path.

## 5. Observability Setup

| Layer | Tool | What's Captured |
|---|---|---|
| Distributed tracing | LangSmith | Every LLM call, tool invocation, and token count as a trace. Linked to session via run_id. |
| Request metrics | In-app MetricsCollector | Request count, latency p50/p95/p99, error rate, uptime |
| LLM performance | In-app MetricsCollector | Inference latency per call, token usage (input/output), call count |
| Tool performance | In-app MetricsCollector | Per-tool call count, latency, error rate |
| Verification tracking | In-app MetricsCollector | How often each safety check triggers (interaction, allergy, prescriptive language) |
| Error categorization | In-app MetricsCollector | Errors by category: openemr_api, timeout, connection, langsmith, unexpected |
| User feedback | LangSmith feedback API | Thumbs up/down per response, linked to trace via run_id |
| Eval regression | SQLite eval_history | Pass rate per run, category breakdown, >5% drop detection |

All metrics are exposed via `GET /metrics` as a single JSON payload. The
MetricsCollector is an in-memory singleton (thread-safe, no external dependencies)
that resets on restart — suitable for a sidecar that restarts with deploys.

See [cost-analysis.md](cost-analysis.md) for token usage projections derived
from the observability data model.

## 6. Open Source Contribution

The agent is packaged as **`openemr-agent`** on PyPI — a reusable clinical agent
toolkit that other OpenEMR deployments can install and customize.

| Artifact | Description |
|---|---|
| PyPI package | `pip install openemr-agent` — includes agent, tools, verification, metrics |
| Source | `agent/` directory in the OpenEMR repository |
| License | GNU GPL v3 (same as OpenEMR) |

The package provides: 8 clinical tools (patient data + drug safety), a verification
layer for healthcare-specific safety checks, an in-memory metrics collector, and
a FastAPI server with OAuth2 integration. It is designed to be extended with
additional tools or swapped to a different LLM provider by changing the config.
