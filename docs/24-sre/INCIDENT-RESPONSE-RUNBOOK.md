# Operational Incident Response, On-Call, and Runbook Catalog

Status: Accepted
Initiative: REVPILOT
Phase: Phase 08 — Production Readiness, Release Governance & Operational Evidence
Owner Role: SRE Lead & Incident Commander
Approver: Dương Vinh
Last Reviewed Date: 2026-09-03
Traceability: `INV-REL-001..002`, `INV-TEN-001..003`, `INV-SEC-001`, `INV-ACT-001`, `NFR-AVL-001`, `NFR-REC-001`, `ADR-0008`
Version: v1.0

---

## 1. Purpose
Defines the standard operational triage, containment, diagnostic, mitigation, and post-incident investigation procedures for RevPilot AI production services.

## 2. Scope
Applies to all production on-call engineers, incident commanders, and platform operators responding to alerts, service degradations, security breaches, and data anomalies.

## 3. Non-Goals
- Authorizing destructive direct database edits or bypassing approval workflows during live incidents.
- Performing uncontrolled ad-hoc hotfixes without code review and audit logging.

## 4. Incident Response Lifecycle and Command Hierarchy

```
[Detection / Page] --> [Containment (<15m)] --> [Diagnostic / Triage] --> [Mitigation] --> [Validation] --> [Post-Mortem / RCA]
```

- **Incident Commander (IC)**: Holds operational authority; coordinates communication and approves remediation actions.
- **Operations Lead (Ops)**: Executes containment actions, checks diagnostic telemetry, runs playbooks.
- **Communications Lead (Comms)**: Manages customer and internal executive updates on a 30-minute cadence.

---

## 5. Master Incident Runbook Catalog

### 5.1 RB-01: Data Isolation Suspicion or Tenant Leak
- **Symptoms**: Cross-tenant record in response, RLS violation alarm `database_rls_violations_total > 0`, customer report.
- **Severity**: P0 (Emergency)
- **Immediate Containment**:
  1. Trigger cluster-wide kill-switch: `python scripts/ops/kill_switch.py --all-agents --block-ingress`.
  2. Suspend target tenant sessions via IAM Admin API.
- **Diagnostic Signals**: Check PostgreSQL query logs filtered by `revpilot.tenant_id`; review recent migration commits.
- **Safe Actions**: Terminate active API pods; dump container memory and query buffers to isolated bucket.
- **Prohibited Actions**: DO NOT run raw `UPDATE` or `DELETE` on production database without dual approval.
- **Escalation**: Notify Security Officer, Principal Architect, and Legal Counsel immediately ($< 15$m).
- **Communication**: Issue P0 customer advisory within 30 minutes following legal clearance.
- **Recovery**: Identify faulty query or policy; deploy patched migration; run isolation test suite before unblocking.
- **Validation**: Run `pytest tests/tenancy/test_cross_tenant_isolation_matrix.py` in staging/canary.
- **Evidence Retention**: Preserve raw database audit logs, network captures, and pod core dumps for 365 days.

### 5.2 RB-02: Runaway AI Model Cost or Inference Loop
- **Symptoms**: `finops.spend.velocity_usd_per_min > threshold`, token consumption spike, P90 agent loop $> 10$ steps.
- **Severity**: P1 (Critical)
- **Immediate Containment**:
  1. Activate AI Gateway spend cap kill-switch: `python scripts/ops/throttle_model_calls.py --cap-per-min 50`.
  2. Revoke agent tool delegation tokens for runaway investigation IDs.
- **Diagnostic Signals**: Filter OpenTelemetry traces by `gen_ai.usage.total_tokens` and `agent.loop_iteration`.
- **Safe Actions**: Scale down agent reasoning worker pool to 1 replica; reject new non-critical investigations.
- **Prohibited Actions**: DO NOT hard-reset database or delete usage ledger tables.
- **Escalation**: Page FinOps Lead and AI Platform Lead.
- **Recovery**: Pin agent to conservative max iterations ($N=3$); restart workers with reduced concurrency.
- **Validation**: Confirm spend velocity drops to baseline within 5 minutes.
- **Evidence Retention**: Archive token usage records and trace trees in `evidence/incidents/`.

### 5.3 RB-03: Audit Logging Pipeline Failure
- **Symptoms**: `audit_events_dropped_total > 0`, hash chain verification cron failure, disk full on audit sink.
- **Severity**: P0 (Emergency) — System violates immutable audit invariant `INV-AUD-001`.
- **Immediate Containment**:
  1. Transition Tool Gateway into fail-closed state (`INV-REL-001`): all external mutations rejected with 503.
  2. Freeze user action dispatches.
- **Diagnostic Signals**: Inspect audit buffer queue depth; check PostgreSQL disk space and WAL replication status.
- **Safe Actions**: Expand audit volume storage; restart audit ingestion worker.
- **Prohibited Actions**: DO NOT bypass audit queue to allow actions to proceed unlogged.
- **Escalation**: Page SRE Lead and Security Lead.
- **Recovery**: Drain audit buffer; verify hash chain continuity from last confirmed block.
- **Validation**: Execute `python scripts/audit/verify_hash_chain.py --full-scan`.
- **Evidence Retention**: Full disk image of audit partition preserved.

### 5.4 RB-04: Upstream Identity Provider (OIDC / SAML) Outage
- **Symptoms**: HTTP 401 spike on `/auth/callback`, JWKS fetch failure `identity.jwks.errors > 10/min`.
- **Severity**: P1 (Critical)
- **Immediate Containment**: Keep existing valid user sessions active (grace period up to session TTL); reject new IdP logins gracefully.
- **Diagnostic Signals**: Check external IdP status dashboard; inspect DNS and egress firewall for JWKS endpoint.
- **Safe Actions**: Switch to backup IdP endpoints if configured in `oidc_federation_configs`.
- **Prohibited Actions**: DO NOT disable JWT signature validation or bypass authentication checks.
- **Escalation**: Alert Customer Success and On-Call SRE.
- **Recovery**: Once IdP resolves, flush failed JWKS cache; verify code exchange flow.
- **Validation**: Synthetic canary login transaction successfully completes.
- **Evidence Retention**: Retain IdP error responses and HTTP headers.

### 5.5 RB-05: Connector Auth Expiry or Provider Rate Limit
- **Symptoms**: Connector transitions to `AUTH_EXPIRED` or `DEGRADED`, sync lag $> 60\text{min}$.
- **Severity**: P2 (Major)
- **Immediate Containment**: Pause automated sync worker for affected connector instance; notify tenant admin via webhook.
- **Diagnostic Signals**: Inspect `connector_instances` state table; verify OAuth refresh token validity.
- **Safe Actions**: Trigger tenant admin re-authorization email; apply exponential backoff to sync interval.
- **Prohibited Actions**: DO NOT attempt rapid credential brute-forcing against provider API.
- **Escalation**: Integrations on-call engineer.
- **Recovery**: Tenant admin completes OAuth re-auth; connector state updates to `ACTIVE`.
- **Validation**: Trigger manual test sync; verify sync lag returns to $< 5\text{min}$.
- **Evidence Retention**: Provider error payload stored in connector quarantine logs.

### 5.6 RB-06: Database Unavailability or Replica Lag
- **Symptoms**: Connection pool exhaustion, P99 query latency $> 5000\text{ms}$, read replica lag $> 300\text{s}$.
- **Severity**: P0 (Emergency)
- **Immediate Containment**: Enable aggressive API read caching; pause non-essential background ETL workers.
- **Diagnostic Signals**: `pg_stat_activity`, active connection count, locks, disk I/O metrics.
- **Safe Actions**: Terminate idle backend connections; initiate managed failover to standby replica if primary node unresponsive.
- **Prohibited Actions**: DO NOT execute manual restart without capturing active lock tables.
- **Escalation**: Database Administrator and Primary SRE.
- **Recovery**: Promote standby replica; update connection strings; verify RLS policies intact.
- **Validation**: Run database health check probe across all tenant schemas.
- **Evidence Retention**: PostgreSQL error logs and `pg_stat_statements` snapshot.

### 5.7 RB-07: Temporal Workflow Engine Crash Loop
- **Symptoms**: `temporal_workflow_task_failed_total > 50`, worker heartbeats dropping, investigate workflow stuck.
- **Severity**: P1 (Critical)
- **Immediate Containment**: Halt deployment of new workflow definitions; scale up workflow worker replicas.
- **Diagnostic Signals**: Temporal Web UI task queue latency; worker panic logs; unhandled exception stack traces.
- **Safe Actions**: Restart stuck worker pods; route new workflows to previous task queue version.
- **Prohibited Actions**: DO NOT terminate active workflows in bulk without checking Saga compensation states.
- **Escalation**: Workflow Engine Lead.
- **Recovery**: Patch non-deterministic workflow code; replay history through Temporal test runner.
- **Validation**: Verify stuck workflows resume and complete without state divergence.
- **Evidence Retention**: Temporal execution history JSON exports.

### 5.8 RB-08: Suspicious Administrative Access or Credential Compromise
- **Symptoms**: Unusual geolocation for operator login, privilege escalation attempt, unexpected secret read.
- **Severity**: P0 (Emergency)
- **Immediate Containment**:
  1. Revoke operator session tokens immediately.
  2. Rotate master credential broker KMS keys (`python scripts/ops/rotate_keys.py --emergency`).
- **Diagnostic Signals**: Review IAM audit log `identity.operator.login` and KMS decrypt calls.
- **Safe Actions**: Isolate operator bastion host; freeze administrative endpoints.
- **Prohibited Actions**: DO NOT delete operator accounts before capturing full session audit logs.
- **Escalation**: Chief Information Security Officer (CISO) and SRE Lead.
- **Recovery**: Re-issue hardware MFA keys; re-validate all active credentials.
- **Validation**: Complete audit verification of all administrative actions executed in preceding 48 hours.
- **Evidence Retention**: Cryptographic seal of all cloud provider audit and VPC flow logs.

---

## 6. Post-Incident Review (PIR) and Root Cause Analysis (RCA)
1. **Mandatory Timeline**: Blameless RCA document drafted within 48 hours for all P0 and P1 incidents.
2. **Standard Template**: Incident Timeline, Root Cause, Contributing Factors, Detection Gap, Mitigation Assessment, Action Items (Preventative + Detective).
3. **Action Item Tracking**: Action items assigned P1 priority in Jira; must be completed within 14 business days.
