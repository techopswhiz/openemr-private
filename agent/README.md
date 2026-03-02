# openemr-agent

Healthcare AI agent sidecar for [OpenEMR](https://www.open-emr.org) -- clinical
decision support with drug interaction checking, patient data retrieval, and
safety verification.

## Features

- **8 clinical tools**: patient lookup, medications, allergies, problems, vitals,
  appointments, drug interaction checking (NLM RxNorm), allergy-drug cross-check
- **3 verification checks**: interaction severity flagging, allergy conflict
  detection, prescriptive language guard
- **LangGraph state machine**: 5-node agent with conditional tool routing
- **Built-in observability**: request/LLM/tool latency tracking, token usage,
  error categorization, eval regression detection
- **FastAPI server**: `/chat`, `/metrics`, `/health`, `/feedback` endpoints
- **OAuth2 integration**: SMART on FHIR scopes for secure OpenEMR API access

## Quick Start

```bash
pip install openemr-agent
```

Create a `.env` file:

```env
XAI_API_KEY=your-xai-key
OPENEMR_BASE_URL=http://localhost:8300
OPENEMR_CLIENT_ID=your-oauth-client-id
OPENEMR_CLIENT_SECRET=your-oauth-client-secret
LANGCHAIN_API_KEY=your-langsmith-key  # optional
```

Run the agent:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full architecture
document including the agent state machine, verification strategy, and
observability setup.

## Cost

See [docs/cost-analysis.md](docs/cost-analysis.md) for production cost
projections. TL;DR: ~$0.002 per clinical query using Grok 3 Mini Fast.

## License

GNU General Public License v3 -- same as OpenEMR.
