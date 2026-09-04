# ADR-0012 — Action Approval and Autonomy Boundary

Status: Accepted  
Date: 2026-09-04  
Owner: Principal Architecture + Security Architecture  
Approver: Dương Vinh  

## Context

RevPilot AI generates operational recommendations and can interface with enterprise execution systems via Tool Gateway. Unbounded autonomous execution of financial actions, contract changes, or external customer messaging poses unacceptable legal, financial, and regulatory risk. Conversely, requiring manual approval for read-only investigations or dry-runs introduces operator fatigue.

## Decision

1. **Zero Unbounded Autonomy**: RevPilot strictly prohibits autonomous money movement, contract modification, or outbound customer communications in MVP and v1 releases.
2. **Deterministic Risk Tiering**: Every action is assigned a static risk tier:
   - **Tier 0 (Read-Only/Dry-Run)**: Fully automated execution within tenant boundaries.
   - **Tier 1 (Internal/Reversible)**: Automated execution permitted only within tenant-configured budget thresholds; requires notification.
   - **Tier 2 (Commercial/Financial Impact)**: Mandatory single human-in-the-loop approval.
   - **Tier 3 (High-Risk/Irreversible/Bulk)**: Mandatory dual-key authorization (two distinct authorized principals) and policy re-validation.
3. **Cryptographic Approval Binding**: Approval tokens bind SHA-256 digest of (tenant_id, action_type, payload_hash, cost_ceiling, expires_at). If the payload or policy state mutates prior to dispatch, the token is invalidated.
4. **Agent Self-Approval Prohibited**: AI agents, autonomous workflows, and service accounts cannot approve Tier 2 or Tier 3 actions (INV-ACT-003).
5. **Instant Emergency Kill-Switches**: Cluster-wide, tenant-wide, and adapter-level kill-switches propagate within 500ms to immediately abort pending or in-flight side effects (INV-REL-001).

## Decision Drivers

INV-ACT-001..004, INV-SEC-001, PRD §Product Constraints, risk of catastrophic financial hallucination, customer trust, auditability.

## Alternatives

- **Dynamic Confidence Autonomy**: Allow high-confidence AI decisions (>99%) to execute without human approval. *Rejected*: Model confidence does not equate to business correctness and creates uninsurable liability.
- **Universal Human Approval**: Require human approval for all tool invocations. *Rejected*: Causes severe operator fatigue and renders background investigations unusable.

## Why Selected

Establishes mathematical boundaries and cryptographic non-repudiation between recommendation and physical side effects, ensuring humans retain ultimate financial authority.

## Pros

- Eliminates runaway automated financial loss.
- Cryptographic binding prevents payload tampering between approval and execution.
- Clear separation of duties enforces compliance readiness (SOC 2 CC6.3).

## Cons

- Requires human review latency for high-tier actions.
- Requires maintenance of human approval queues and escalation timeouts.

## Consequences

- Tool Gateway must verify approval digest and active kill-switches prior to dispatching any external API request.
- All actions are logged to an append-only, tamper-evident action ledger (INV-ACT-004).

## Risks

Approval fatigue leading to rubber-stamping. Mitigate with concise evidence digests, blast radius caps, and approval timeout expiration.

## Security Impact

Enforces defense-in-depth: untrusted LLM generation cannot directly cause physical mutations without human cryptographic authorization.

## Tenancy Impact

Approval thresholds, authorized approver roles, and action blast ceilings are strictly tenant-isolated.

## Operational Impact

Requires dedicated UI approval center, mobile/email notification workflows, and on-call escalation policies.

## Cost Impact

Prevents catastrophic unintended API invocations and financial commitments; small compute overhead for cryptographic hashing.
