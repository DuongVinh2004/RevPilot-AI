# Risk Register

Status: Proposed v0.1

| ID | Risk | Probability/Impact | Treatment | Owner | Trigger |
|---|---|---|---|---|---|
| `RISK-001` | Scope exceeds team/time capacity | High/High | Vertical slices; defer P2/P3; component “why now” gate | Product/Architecture | Phase slips or orphan specs |
| `RISK-002` | Incorrect causal claim drives harmful action | Medium/Critical | Multiple hypotheses, sensitivity, verifier, approval, conservative eligibility | ML/Product | Poor overlap/unstable effect |
| `RISK-003` | Cross-tenant leakage | Medium/Critical | Defense-in-depth and cross-store negative matrix | Security/Data | Any tenant-context mismatch |
| `RISK-004` | Prompt/tool injection | High/High | Untrusted-data boundary, typed tools, gateway, policy, adversarial eval | AI/Security | Tool intent sourced from documents |
| `RISK-005` | Duplicate irreversible action | Medium/Critical | Ledger, idempotency, reconciliation, blast limits | Execution | Timeout after provider acceptance |
| `RISK-006` | Schema drift silently corrupts metrics | High/High | Contracts, quarantine, reconciliation, metric versioning | Data | Unmapped/semantic source change |
| `RISK-007` | Runaway inference cost | Medium/High | Hierarchical budgets, loop/tool limits, kill switch | FinOps/AI | Cost anomaly or repeated retry |
| `RISK-008` | Advanced stack becomes distributed monolith | Medium/High | Modular monolith; ADR/service-extraction thresholds | Architecture | Service added without boundary owner |
| `RISK-009` | Synthetic benchmark overstates real performance | High/Medium | Holdout incidents, noise/drift profiles, later pilot validation | ML/Product | Large synthetic-to-pilot gap |
| `RISK-010` | Approval fatigue causes rubber-stamping | Medium/High | Calibrated tiers, concise evidence, expiry, audit analytics | Product/Risk | High approval rate/low review time |
| `RISK-011` | Provider lacks reliable idempotency/reconciliation | Medium/High | Adapter-specific policy; disable unsafe action | Integrations | Provider capability review fails |
| `RISK-012` | Audit logging creates privacy risk | Medium/High | Metadata/hash audit, encrypted evidence, retention/access policy | Security/Privacy | Raw PII appears in immutable sink |
| `RISK-013` | Proposed ADRs are mistaken for implementation authorization | Medium/High | Precedence rules, Rail 0 RED, empty executor queue, explicit ADR approval | Architecture/Planning | Task cites Proposed ADR as implementation-ready |
| `RISK-014` | Unknown cloud/model provider/legal terms block safe commercial design | High/High | Track UNKNOWN owners in boundaries/workload/ADRs; block dependent adapter/onboarding tasks | Product/Architecture/Security/Privacy | Before production provider or first commercial contract |
| `RISK-015` | No Git/toolchain baseline prevents leased diffs and exact verification | Certain/Medium | Keep executor queue empty; define/approve bootstrap and validation tasks later | Developer Platform | Before any Stage B task |

## Foundation mitigation evidence

These are design artifacts, not implemented controls: `RISK-001/008` map to ADR-0001/0008 and workload tiers; `RISK-003` maps to ADR-0005 and `INV-TEN-*`; `RISK-004` maps to system boundaries, ADR-0003/0011 and `INV-SEC-*`; `RISK-005/011` map to `INV-ACT-*`; `RISK-007` maps to the workload cost budget and `INV-COST-001`; `RISK-012` maps to ADR-0010 and `INV-AUD-002`/`INV-PRV-001`. Risk probability/impact is not reduced until implementation and test evidence exists.
