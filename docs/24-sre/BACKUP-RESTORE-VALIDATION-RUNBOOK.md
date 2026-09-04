# Backup, Restore, and Point-in-Time Recovery Validation Runbook

Status: Accepted
Initiative: REVPILOT
Phase: Phase 08 — Production Readiness, Release Governance & Operational Evidence
Owner Role: SRE Lead & Storage Architect
Approver: Dương Vinh
Last Reviewed Date: 2026-09-03
Traceability: `NFR-REC-001`, `INV-REL-001..002`, `INV-DATA-001`, `INV-TEN-001`, `INV-AUD-001`, `ADR-0008`

---

## 1. Purpose
Defines the technical specifications, automation scripts, encryption requirements, and validation procedures for database snapshots, continuous WAL archiving, object storage backups, and full/tenant-scoped point-in-time restores.

## 2. Scope
Covers primary relational data (PostgreSQL), immutable audit logs, tool execution ledgers, object storage documents, and vector index rebuild routines.

## 3. Non-Goals
- Backing up transient ephemeral caches (Redis), in-memory worker queues, or temporary scratch files.
- Restoring production backups directly onto active production clusters without pre-validation.

## 4. Target Recovery Boundaries

> [!IMPORTANT]
> Design targets only — not yet measured in production. Targets are derived from architecture specifications and subject to validation during scheduled DR exercises.

- **Recovery Point Objective (RPO)**: $\le 5\text{ minutes}$ (continuous WAL streaming to cross-region object storage).
- **Recovery Time Objective (RTO)**: $\le 30\text{ minutes}$ (automated infrastructure provisioning + snapshot hydrate + WAL replay).

---

## 5. Subsystem Backup Matrix and Retention Rules

| Subsystem / Datastore | Data Classification | Backup Mechanism | Frequency | Retention Window | Encryption Standard | Key Dependency |
|---|---|---|---|---|---|---|
| **PostgreSQL (Primary)** | Confidential / PII | Base Snapshot + Continuous WAL stream | Snapshot: Daily<br>WAL: Continuous (5m flush) | Snapshots: 30 Days<br>WAL: 7 Days | AES-256-GCM | Master KMS Key |
| **Audit Ledger DB** | Restricted / Audit | Append-only WAL + Daily Snapshot | Snapshot: Daily<br>WAL: Continuous | Snapshots: 365 Days<br>WAL: 30 Days | AES-256-GCM (WORM) | Audit KMS Key |
| **Object Storage (Evidence)**| Confidential | Versioned Bucket Replication | Continuous (Cross-region) | 365 Days | SSE-KMS / Dual-region | Object KMS Key |
| **Vector DB (Embeddings)** | Internal (Derived) | Disposable Projection — NO BACKUP | Rebuilt from primary doc store on demand | N/A | SSE-KMS | Storage KMS Key |
| **Redis Cache / Sessions**| Ephemeral | NO BACKUP — Cold restart reconstructed | N/A | N/A | AES-256 in transit | N/A |

---

## 6. Automated Backup Validation Procedure (Ephemeral Staging)

To ensure backups are not corrupt, an automated weekly validation cron is planned to execute scoped cold restores in an isolated sandbox environment. This is distinct from the monthly ephemeral restore rehearsal and the bi-annual full DR simulation defined in `DR-PLAN.md`; none is claimed executed until a retained evidence artifact exists.

```mermaid
flowchart LR
  Snap[Nightly Snapshot + WAL] --> Trigger[Weekly Automation Cron]
  Trigger --> Provision[Provision Ephemeral PostgreSQL Instance]
  Provision --> Restore[Restore Snapshot & Replay WAL]
  Restore --> Probe[Run Integrity & Isolation Probes]
  Probe --> Verdict{All Probes Pass?}
  Verdict -->|Yes| Record[Emit CTL-DR-01 Evidence Manifest]
  Verdict -->|No| Alert[Page SRE On-Call (P1 Alert)]
  Record --> TearDown[Destroy Ephemeral Instance]
  Alert --> TearDown
```

### 6.1 Validation Probe Execution
1. **Catalog Integrity Check**: Run `VACUUM FULL ANALYZE` and verify zero table corruption.
2. **Hash Chain Verification**: Scan recent 10,000 audit records and verify unbroken cryptographic hash chain.
3. **Tenant Boundary Probe**: Execute `tests/tenancy/test_tenant_isolation_negative.py` against restored database.
4. **Target Measurement**: Log restore start and finish times to calculate empirical RTO.

---

## 7. Point-in-Time Recovery (PITR) Execution Procedure

When data corruption or bad migration occurs at time $T_{\text{fault}}$:

### 7.1 Pre-Flight Commands
```bash
# 1. Identify target recovery timestamp (e.g. 5 minutes prior to fault)
TARGET_TIME="2026-09-03 14:35:00 UTC"

# 2. Halt traffic ingress to prevent forward data divergence
python scripts/ops/kill_switch.py --all-agents --block-ingress

# 3. Provision target recovery database node
python scripts/dr/provision_recovery_node.py --instance-type db.r6g.2xlarge
```

### 7.2 Restore & WAL Replay
```bash
# 4. Stream base snapshot and replay WAL logs up to TARGET_TIME
python scripts/dr/execute_pitr_restore.py \
  --snapshot-id "snap-prod-20260903-0200" \
  --target-time "$TARGET_TIME" \
  --verify-isolation
```

### 7.3 Secondary Projection Rebuilding
Because Vector DB projections are disposable and not backed up:
```bash
# 5. Trigger asynchronous background re-indexing for affected documents
python scripts/dr/rebuild_vector_projections.py --as-of "$TARGET_TIME"
```

---

## 8. Tenant-Scoped Recovery (Single Tenant Restore)
In multi-tenant schemas where only one tenant suffered accidental corruption:
1. Restore the global snapshot to an isolated staging recovery database.
2. Extract the target tenant's partition using tenant-scoped dump:
   ```bash
   python scripts/dr/extract_tenant_data.py --tenant-id "ten_12345" --output /tmp/ten_12345_restore.sql
   ```
3. In production database, acquire tenant advisory lock.
4. Replace target tenant partition rows within a single serializable transaction.
5. Release tenant advisory lock and re-validate isolation.

## 9. Acceptance Criteria
1. `AC-BKP-01`: Automated weekly restore drill successfully boots staging database, verifies audit hash chain, and tears down instance without human intervention.
2. `AC-BKP-02`: PITR procedure tested in staging environment achieves measured RTO $\le 30$ minutes and RPO $\le 5$ minutes.
