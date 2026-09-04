# Risk Register

Status: Authoritative Post-Phase-08 Risk Register v2.0
Owner: Principal Platform Architect, Security Architect, SRE Lead, Compliance Lead
Approver: Duong Vinh

---

## 1. Risk Evaluation Matrix

| ID | Risk Description | Probability / Impact | Treatment & Controls | Owner | Trigger / Monitor | Status / Closure Record | Residual Risk |
|---|---|---|---|---|---|---|---|
| `RISK-001` | Scope exceeds team/time capacity | High / High | Vertical slices; defer P2/P3; component "why now" gate | Product / Architecture | Phase slips or orphan specs | ACTIVE | Feature delay under complex integrations |
| `RISK-002` | Incorrect causal claim drives harmful action | Medium / Critical | Multiple hypotheses, sensitivity, verifier, approval, conservative eligibility | ML / Product | Poor overlap / unstable effect | ACTIVE | Residual uncertainty in unmeasured domains |
| `RISK-003` | Cross-tenant data leakage | Medium / Critical | In-memory negative isolation suite; PostgreSQL RLS; composite tenant keys | Security / Data | Any tenant context mismatch | ACTIVE (In-memory closed; DB RLS open) | PostgreSQL connection pool leaks |
| `RISK-004` | Prompt / tool injection | High / High | Untrusted-data boundary, typed tools, gateway, policy, adversarial eval | AI / Security | Tool intent sourced from documents | ACTIVE | Zero-day jailbreak techniques |
| `RISK-005` | Duplicate irreversible action | Medium / Critical | Immutable ledger, idempotency keys, reconciliation, blast limits | Execution | Timeout after provider acceptance | ACTIVE | Third-party API non-idempotence |
| `RISK-006` | Schema drift silently corrupts metrics | High / High | Contracts, quarantine queue, reconciliation, metric versioning | Data | Unmapped / semantic source change | ACTIVE | Silent semantic data changes |
| `RISK-007` | Runaway inference cost | Medium / High | Hierarchical budgets, loop/tool limits, circuit breaker kill-switch | FinOps / AI | Cost anomaly or repeated retry | ACTIVE | Provider pricing changes |
| `RISK-008` | Advanced stack becomes distributed monolith | Medium / High | Modular monolith; ADR-0001; service-extraction thresholds | Architecture | Service added without boundary owner | ACTIVE | Coupling between internal modules |
| `RISK-009` | Synthetic benchmark overstates real performance | High / Medium | Holdout incidents, noise/drift profiles, later pilot validation | ML / Product | Large synthetic-to-pilot gap | ACTIVE | Unmodeled edge cases in production |
| `RISK-010` | Approval fatigue causes rubber-stamping | Medium / High | Calibrated risk tiers (T0-T3), concise evidence digest, expiry | Product / Risk | High approval rate / low review time | ACTIVE | Approver carelessness |
| `RISK-011` | Provider lacks reliable idempotency | Medium / High | Adapter-specific policy; disable unsafe actions; reconciliation | Integrations | Provider capability review fails | ACTIVE | Asynchronous failure ambiguity |
| `RISK-012` | Audit logging creates privacy risk | Medium / High | Metadata/hash audit, encrypted evidence, PII sanitization | Security / Privacy | Raw PII appears in immutable sink | ACTIVE | DLP pattern omission |
| `RISK-013` | Architecture documents mistaken for implementation authorization | Low / High | Micro-Task Rail System; fail-closed executor queue; precedence rules | Architecture / Planning | Unadmitted implementation attempted | ACTIVE<br>Documentation control exists; current queue wording is ambiguous and implementation evidence is absent.<br>Owner: Platform Lead | Executor queue or status-report misinterpretation |
| `RISK-014` | Unknown cloud/model/legal terms block commercial design | High / High | Track open decisions (`DEC-001..005`) in register; fail-closed | Architecture / Legal | Commercial tenant discovery | ACTIVE<br>Tracked in `DECISION-CLOSURE-REGISTER.md` | Commercial pilot onboarding delays |
| `RISK-015` | Toolchain or workspace drift compromises exact verification | Low / Medium | Pinned Git baseline (`a541362`), `pyproject.toml`, retained execution artifacts | Developer Platform | Test failure or dependency drift | ACTIVE<br>Historical pytest claim is not current execution evidence; release worktree must be pinned and clean.<br>Owner: DevPlatform Lead | Toolchain and dependency drift |
| `RISK-016` | Premature production declaration without empirical evidence | High / Critical | Phase 08 Production Readiness Gate enforces empirical artifacts; status BLOCKED | SRE / Architecture | Attempt to promote without evidence | ACTIVE<br>Tracked in `OPEN-BLOCKERS.md` (`BLK-005`) | Stakeholder pressure to launch early |
| `RISK-017` | Multi-tier rollback failure corrupts persistent state | Medium / Critical | 13-tier rollback coordination; Expand/Contract database migrations | Release / SRE | Partial rollback attempted | ACTIVE<br>Mitigated by `RELEASE-CANARY-ROLLBACK-SPEC.md` | In-flight transaction abortion |
| `RISK-018` | Silent WAL streaming failure causes RPO breach in DR | Low / Critical | Continuous automated restore rehearsal in ephemeral staging (`CTL-DR-01`) | Storage / SRE | WAL archive lag alarm fires | ACTIVE<br>Mitigated by `BACKUP-RESTORE-VALIDATION-RUNBOOK.md` | Storage provider regional outage |
| `RISK-019` | On-call alert fatigue causes missed critical incidents | Medium / High | Strict severity classification (P0-P4), alert flapping damping | SRE / Ops | Alert fires > 10x/week without issue | ACTIVE<br>Mitigated by `OPERATIONS-TELEMETRY-SPEC.md` | Alert storm during major outage |
| `RISK-020` | AI model provider silent degradation or API retirement | Medium / High | Pinned model snapshots in Model Registry; automated golden set gate | AI Governance | Golden set benchmark score drops | ACTIVE<br>Mitigated by `MODEL-RELEASE-PROCESS.md` | Provider deprecates model version |

---

## 2. Foundation Mitigation Evidence and Traceability Linkage
- `RISK-001/008` map to `ADR-0001`, `ADR-0008`, and `WORKLOAD-ASSUMPTIONS.md`.
- `RISK-003` maps to `ADR-0005`, `INV-TEN-001..003` (domain in-memory closed in Rail 1-2; persistence RLS open in Rail 5).
- `RISK-004` maps to `SYSTEM-BOUNDARIES.md`, `ADR-0003`, `ADR-0011`, and `INV-SEC-002`.
- `RISK-005/011` map to `ADR-0012` and `INV-ACT-001..004`.
- `RISK-007` maps to `FINOPS-SPEC.md` and `INV-COST-001`.
- `RISK-012` maps to `ADR-0010`, `AUDIT-LOG-SPEC.md`, and `INV-AUD-002`/`INV-PRV-001`.
- `RISK-013` closed on 2026-09-03 via authoritative fail-closed Executor Queue.
- `RISK-014` tracked under `DECISION-CLOSURE-REGISTER.md` (`DEC-001..005`) and `OPEN-BLOCKERS.md`.
- `RISK-015` closed on 2026-09-03 via clean Git commit `a541362` and passing 100/100 pytest suite.
- `RISK-016..020` codified in Phase 08 production readiness gates and `execution/evidence/` templates.
