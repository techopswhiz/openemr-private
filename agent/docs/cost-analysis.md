# AI Cost Analysis: OpenEMR Clinical Agent

## 1. Development & Testing Costs

### Actual Development Spend

| Service | Cost | Notes |
|---|---|---|
| xAI API (Grok 3 Mini Fast) | $0.08 | Total YTD spend — development + testing |
| LangSmith | $0.00 | Free tier (5,000 traces/month) |
| DigitalOcean droplet | $24.00/mo | 4GB standard droplet (shared with OpenEMR) |
| RxNorm API (NLM) | $0.00 | Free public API |
| OpenFDA API | $0.00 | Free public API |
| **Total dev cost** | **~$24.08/mo** | Infrastructure-dominated |

The xAI spend is remarkably low ($0.08 total) because Grok 3 Mini Fast is priced
aggressively ($0.30/M input, $0.50/M output) and development involved limited
query volume. This validates the model choice for cost-sensitive healthcare deployments.

### Model Pricing Reference

| Model | Input | Output | Context |
|---|---|---|---|
| xAI Grok 3 Mini Fast | $0.30/M tokens | $0.50/M tokens | 131K context |
| GPT-4o (comparison) | $2.50/M tokens | $10.00/M tokens | 128K context |
| Claude 3.5 Sonnet (comparison) | $3.00/M tokens | $15.00/M tokens | 200K context |

Grok 3 Mini Fast is **8-10x cheaper** than comparable models, making it viable for
high-volume clinical query workloads where cost per query matters.

---

## 2. Production Cost Projections

### Assumptions

| Parameter | Value | Rationale |
|---|---|---|
| Queries per user per day | 5 | Clinical staff checking patients during rounds, pre-visit prep |
| Working days per month | 30 | Healthcare operates daily |
| Avg input tokens per query | 1,500 | System prompt (~500) + conversation history (~400) + tool results (~600) |
| Avg output tokens per query | 800 | LLM response (~500) + tool call arguments (~300) |
| LLM calls per query | 2.5 | Initial call + avg 1.5 tool-use round-trips |
| Verification overhead | $0 | String matching only, no additional LLM calls |

### Per-Query Cost Breakdown

```
Input:  1,500 tokens x 2.5 calls = 3,750 tokens/query x $0.30/M = $0.001125
Output:   800 tokens x 2.5 calls = 2,000 tokens/query x $0.50/M = $0.001000
                                                         Total = $0.002125/query
```

**~$0.002 per clinical query** — roughly 1/5th of a penny.

### Scaling Projections

| Scale | Users | Queries/mo | xAI Cost | LangSmith | Infra | **Total/mo** | **Per-user/mo** |
|---|---|---|---|---|---|---|---|
| Pilot | 100 | 15,000 | $32 | $0 (free tier) | $24 | **$56** | $0.56 |
| Small clinic | 1,000 | 150,000 | $319 | $73 | $48 | **$440** | $0.44 |
| Regional health system | 10,000 | 1,500,000 | $3,188 | $748 | $200 | **$4,136** | $0.41 |
| Large network | 100,000 | 15,000,000 | $31,875 | $7,475 | $2,000 | **$41,350** | $0.41 |

### Cost Component Breakdown

**xAI API** (77% of cost at scale):
- 15K queries/mo: 56.25M input + 30M output tokens = $16.88 + $15.00 = $31.88
- Scales linearly with query volume
- No minimum commitment, pay-as-you-go

**LangSmith Observability** (18% of cost at scale):
- Free tier: 5,000 traces/month (covers pilot)
- Paid: $0.50 per 1,000 traces
- Each query = 1 trace (includes all tool calls)
- Can be disabled in production to save costs if LLM-level logging suffices

**Infrastructure** (5% of cost at scale):
- DigitalOcean droplet: $24/mo base (4GB), scales with load
- Agent sidecar is stateless — horizontal scaling via multiple containers
- OpenEMR itself needs its own infra (not included — already deployed)

| Scale | Estimated infra | Configuration |
|---|---|---|
| 100 users | $24/mo | Single 4GB droplet |
| 1K users | $48/mo | 8GB droplet or 2x4GB |
| 10K users | $200/mo | Load-balanced 3-node cluster |
| 100K users | $2,000/mo | Auto-scaling cluster + dedicated DB |

---

## 3. Cost Optimization Strategies

### Immediate (no code changes)
- **Disable LangSmith in production** — save 18% at scale. Keep for staging/dev only.
- **Response caching** — identical drug interaction queries can be cached (RxNorm data is static). Could reduce xAI costs by 20-30%.

### Medium-term
- **Prompt compression** — system prompt is sent with every LLM call. Caching or shortening it saves ~500 tokens/call.
- **Batch tool calls** — when the agent needs multiple patient data points, a single combined API call is cheaper than sequential LLM round-trips.

### Long-term
- **Fine-tuned smaller model** — a fine-tuned Grok Mini on clinical QA could reduce token usage and improve accuracy simultaneously.
- **Self-hosted inference** — at 100K+ users, self-hosting a quantized model on GPU instances could be cheaper than API pricing.

---

## 4. Comparison: Build vs. Buy

| Approach | Monthly cost (1K users) | Pros | Cons |
|---|---|---|---|
| This agent (Grok 3 Mini) | ~$440 | Cheapest, customizable, open source | Requires maintenance |
| OpenAI GPT-4o equivalent | ~$3,200 | Higher quality responses | 8x more expensive |
| Commercial clinical AI SaaS | $5,000-20,000 | Turnkey, supported | Vendor lock-in, no customization |

The open-source agent approach at $0.44/user/month is **7-45x cheaper** than alternatives,
making clinical AI accessible to small practices and community health centers that
typically cannot afford commercial AI solutions.
