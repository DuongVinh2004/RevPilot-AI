# Workload and Capacity Assumptions

Status: Accepted v1.0
Owner: Principal Architecture + SRE  
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Date: 2026-09-04
Evidence state: No production measurements exist. Every number below is a `DESIGN ASSUMPTION`, `DESIGN TARGET`, or `UNKNOWN`.

## Capacity tiers

| Tier | Intended use | Tenant shape |
|---|---|---|
| DEVELOPMENT | Individual local engineering and tests | 1 synthetic tenant |
| DEMO / PORTFOLIO | Reproducible flagship demonstration | 3 synthetic tenants including negative isolation data |
| INITIAL COMMERCIAL | Controlled paid pilots | 25 tenants: design assumption 20 SMB, 5 Enterprise |
| GROWTH | Evidence-driven scale horizon, not current commitment | Up to 250 tenants: 200 SMB, 45 Enterprise, 5 Regulated |
| ENTERPRISE | Large dedicated-tenant envelope | Per-tenant dedicated resources where ADR-0005 triggers apply |

## Planning matrix

All values are unmeasured. Confidence describes planning confidence, not service quality.

| Dimension | Development | Demo | Initial Commercial | Growth | Enterprise envelope | Type | Why needed | Confidence | Revisit trigger |
|---|---:|---:|---:|---:|---:|---|---|---|---|
| Tenants | 1 | 3 | 25 | 250 | 1 dedicated | DESIGN ASSUMPTION | Isolation/capacity topology | Medium | Signed pipeline exceeds tier or tenant mix changes 25% |
| Users per tenant | 5 | 10 | median 25, max 100 | median 50, max 500 | max 1,000 | DESIGN ASSUMPTION | IAM/session/load | Low | First pilot discovery or p95 differs 2x |
| Concurrent users total | 2 | 10 | 100 | 1,000 | 250 per tenant | DESIGN TARGET | API/UI capacity | Low | 15-minute peak exceeds 80% target twice |
| Investigations/day | 20 | 100 | 500 | 10,000 | 1,000 per tenant | DESIGN ASSUMPTION | Workflow/model budget | Low | 30-day p95 exceeds 80% |
| Concurrent active investigations | 2 | 5 | 20 | 200 | 50 per tenant | DESIGN TARGET | Worker/DB/model concurrency | Medium | Queue wait p95 >30 s for 3 windows |
| Automated investigation duration | p95 15 min | p95 15 min | p95 20 min | p95 20 min | p95 30 min | DESIGN TARGET | Workflow timeout/capacity | Low | Real stage budgets or provider latency invalidate target |
| Approval wait retention | 7 days | 7 days | 30 days | 30 days | 90 days | DESIGN ASSUMPTION | Durable workflow/history | Medium | Customer policy requires longer |
| Simultaneous waiting approvals | 10 | 20 | 1,000 | 20,000 | 5,000 | DESIGN ASSUMPTION | Temporal/storage/UI | Low | 30-day peak exceeds 80% |
| Orders/day ingested | 10k | 100k | 1M | 50M | 10M per tenant | DESIGN ASSUMPTION | Data/metric/storage | Low | Pilot source inventory differs 2x |
| CRM tickets/day | 1k | 10k | 100k | 5M | 1M per tenant | DESIGN ASSUMPTION | NLP/retrieval | Low | Pilot differs 2x |
| Documents/tenant | 100 | 1k | median 10k, max 50k | median 100k, max 1M | 1M | DESIGN ASSUMPTION | Ingestion/index sizing | Low | Any tenant reaches 70% maximum |
| Document size | avg 2 MB, max 25 MB | same | same | same | max subject to contract | DESIGN TARGET | Parser/object limits | Medium | Valid business corpus needs larger files |
| Vector chunks total | 50k | 500k | 10M | 500M | 100M per tenant | DESIGN ASSUMPTION | Retrieval ADR | Low | Validated corpus or p95 trigger reached |
| Incremental sync cadence | 15 min | 15 min | 5–15 min | 1–15 min | tenant contract | DESIGN TARGET | Freshness | Low | Business SLA requires <1 min or CDC |
| Webhook/event sustained rate | 10/s | 50/s | 100/s, burst 500/s | 2k/s, burst 10k/s | 1k/s per tenant | DESIGN ASSUMPTION | Outbox/Kafka trigger | Low | 15-min sustained >100/s or backlog target fails |
| Product API sustained rate | 5 rps | 20 rps | 100 rps | 2,000 rps | 500 rps per tenant | DESIGN TARGET | API capacity | Low | p95 latency fails at 70% load |
| External tool actions/day | 0 real | 0 real | 5k | 250k | 50k per tenant | DESIGN ASSUMPTION | Gateway/audit/provider quota | Low | Contract/provider limits differ |
| Recipients per action run | 0 real; dry-run only | 0 real; dry-run only | default max 100 | default max 100 | configurable max 500 with high-tier approval | DESIGN TARGET | Blast radius | Medium | Risk owner approves changed cap |
| Model calls/investigation | target median <=12; hard max 40 | same | same | target <=10 through routing/cache | tenant budget | DESIGN TARGET | Cost/loop control | Medium | Quality gate needs more or cost exceeds budget |
| Total model input tokens/investigation | target <=200k; hard max 500k | same | same | target <=150k | tenant budget | DESIGN TARGET | Context/cost control | Low | Eval proves different quality/cost frontier |
| Model cost/investigation | target <=USD 2; hard stop USD 5 | same simulated | same default | target <=USD 1.50 | contract budget | DESIGN TARGET | Gross margin/abuse control | Low | Provider price/quality or COGS changes 20% |
| Transactional retention | 90 days test | 2 years | 2 years default | 2 years default | contract/legal | DESIGN ASSUMPTION | Storage/deletion design | Low | Legal/customer requirement established |
| Immutable audit retention | local test only | 1 year simulation | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Legal/compliance requirement | None | Privacy/legal and customer contracts decide |

## Service and recovery targets

| Target | Development/Demo | Initial Commercial | Growth | Classification | Revisit trigger |
|---|---|---|---|---|---|
| Product API availability | Best effort | 99.9% monthly | 99.95% monthly | DESIGN TARGET | SLO/error-budget review |
| Durable workflow availability | Best effort | 99.9% monthly | 99.95% monthly | DESIGN TARGET | Managed Temporal design/SLO evidence |
| Synchronous product API p95 | <1 s | <500 ms excluding async work | <500 ms | DESIGN TARGET | 3 consecutive windows breach |
| User-visible workflow event propagation p95 | <10 s | <5 s | <5 s | DESIGN TARGET | 3 consecutive windows breach |
| RPO/RTO for transactional state | Rebuild/test fixtures | 5 min / 30 min | 5 min / 30 min | DESIGN TARGET | Business impact analysis changes |
| Model/RAG quality | Offline benchmark only | Per evaluation release gate | Per tenant/global gate | DESIGN TARGET | Model/data change |

## Capacity decision rules

- A single spike does not trigger rearchitecture; a trigger requires the observation window named by its ADR or a contractual/security requirement.
- Tenant isolation, authorization, audit, idempotency, and cost hard limits must hold at 120% of accepted peak load in validation.
- Growth figures justify designing seams, not provisioning Growth infrastructure during MVP.
- Measured values, once available, are stored in dated benchmark/SLO reports and never overwrite this assumption record silently.

