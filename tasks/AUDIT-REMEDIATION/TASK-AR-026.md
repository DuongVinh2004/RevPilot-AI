# TASK-AR-026 — Production IaC Hardening — Secrets, Deletion Protection, Egress

TYPE: MICRO-TASK
STATUS: PASS
RAIL: 18
INITIATIVE: REVPILOT
PHASE: AUDIT-REMEDIATION
EPIC: IAC-CICD
FEATURE: IAC-HARDEN
COMPLEXITY: M
REASONING_LOAD: MEDIUM
READINESS_SCORE: 18/20
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0
PARALLEL_SAFE: NO
PARALLEL_WITH: NONE
DEPENDS_ON: AR-027
UNLOCKS: NONE

## Objective and rationale

OBJECTIVE: Harden staging Terraform infrastructure and instantiate hardened production environment configuration under `infra/environments/production/`. Inject `DATABASE_URL` secrets reference into ECS task definitions, enforce database deletion protection, set non-zero Secrets Manager recovery windows (>= 7 days), and enforce strict network egress allowlists eliminating unrestricted `0.0.0.0/0` outbound access in production.

BUSINESS RATIONALE: Zero-trust audit finding P1-IAC-001 identified multiple infrastructure vulnerabilities in the Terraform codebase:
1. Database deletion protection was disabled (`deletion_protection = false`), creating severe data-loss risk.
2. Secrets Manager `recovery_window_in_days = 0` eliminated recovery capability for deleted secrets.
3. ECS tasks lacked explicit `DATABASE_URL` secrets injection from AWS Secrets Manager in container definitions.
4. Security groups contained open `0.0.0.0/0` outbound rules violating egress lockdown principles.
5. No production environment configuration existed under `infra/environments/production/`.
Hardening IaC across environments prevents catastrophic state loss, enforces credential encryption at rest, and ensures zero egress leakage.

ARCHITECTURAL OWNER: Cloud Platform Architect / DevSecOps Lead

ARCHITECTURAL CONTEXT: INV-SEC-001 (secrets management and credential isolation), DEC-004 (AWS ECS/RDS production topology), ADR-0004 (PostgreSQL Aurora persistence), ADR-0009 (secrets and keys), `docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md` §5-§6.

## Canonical specification references

- `docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md`
- `docs/31-adr/ADR-0004-postgresql-aurora.md`
- `docs/31-adr/ADR-0009-secrets-and-keys.md`
- `AGENTS.md#3-strict-prohibitions`
- `execution/DEFINITION-OF-DONE.md`

If references conflict, return BLOCKED.

## Preconditions

- AR-027 PASS (IaC directory structure and CI linting established).
- `infra/environments/staging/` exists with working Terraform manifests.
- AWS provider version constraints pinned in `versions.tf`.

## Change boundary

READ_SET:
- `infra/environments/staging/*.tf` (all 10 files)
- `docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md`
- `docs/31-adr/ADR-0009-secrets-and-keys.md`

WRITE_SET:
- `infra/environments/staging/ecs.tf`
- `infra/environments/staging/security_groups.tf`
- `infra/environments/staging/rds.tf`
- `infra/environments/staging/secrets.tf`
- `infra/environments/production/alb.tf`
- `infra/environments/production/ecs.tf`
- `infra/environments/production/kms.tf`
- `infra/environments/production/outputs.tf`
- `infra/environments/production/rds.tf`
- `infra/environments/production/secrets.tf`
- `infra/environments/production/security_groups.tf`
- `infra/environments/production/variables.tf`
- `infra/environments/production/versions.tf`
- `infra/environments/production/vpc.tf`

CREATE:
- `infra/environments/production/alb.tf`
- `infra/environments/production/ecs.tf`
- `infra/environments/production/kms.tf`
- `infra/environments/production/outputs.tf`
- `infra/environments/production/rds.tf`
- `infra/environments/production/secrets.tf`
- `infra/environments/production/security_groups.tf`
- `infra/environments/production/variables.tf`
- `infra/environments/production/versions.tf`
- `infra/environments/production/vpc.tf`

MODIFY:
- `infra/environments/staging/ecs.tf` — add `secrets` array with `DATABASE_URL` secret reference in container definitions.
- `infra/environments/staging/rds.tf` — set `deletion_protection = true`.
- `infra/environments/staging/secrets.tf` — set `recovery_window_in_days = 7`.
- `infra/environments/staging/security_groups.tf` — restrict egress to designated gateway/VPC endpoint ranges.

DO_NOT_MODIFY:
- `apps/*`
- `packages/*`
- `tests/*`
- Any file outside WRITE_SET

EXPECTED CHANGE SET:
- 4 modified staging Terraform manifests.
- 10 new production Terraform manifests establishing an isolated, locked-down production topology.

## Symbol-level contract

MUST EXPORT/DEFINE:
- In `infra/environments/staging/ecs.tf` and `infra/environments/production/ecs.tf`:
  - `aws_ecs_task_definition.api`:
    - `container_definitions` includes `secrets`:
      ```hcl
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.platform_config.arn}:DATABASE_URL::"
        }
      ]
      ```
- In `infra/environments/staging/rds.tf` and `infra/environments/production/rds.tf`:
  - `aws_rds_cluster.aurora`:
    - `deletion_protection = true`
    - `backup_retention_period >= 7` (35 in production)
- In `infra/environments/staging/secrets.tf` and `infra/environments/production/secrets.tf`:
  - `aws_secretsmanager_secret.platform_config`:
    - `recovery_window_in_days >= 7` (30 in production)
- In `infra/environments/production/security_groups.tf`:
  - Zero occurrences of `0.0.0.0/0` in CIDR blocks.
  - ALB ingress restricted to CloudFront managed prefix list or explicit IP ranges.
  - Egress rules restricted to internal VPC CIDR, VPC endpoints, and explicit proxy CIDRs.

MUST NOT:
- Contain `deletion_protection = false` in any environment manifest.
- Contain `0.0.0.0/0` anywhere in `infra/environments/production/`.
- Contain `recovery_window_in_days = 0` in any environment manifest.
- Embed plaintext credentials, tokens, or private keys in Terraform files.

## Input/output and validation

INPUT: Terraform configuration variables (`variables.tf` in staging and production).
OUTPUT: Declared AWS infrastructure topology (VPC, Subnets, SG, KMS, Secrets, RDS Aurora, ECS Fargate, ALB).
INVALID INPUT: Unencrypted storage, deletion protection disabled, or open egress CIDRs.
VALIDATION RULES:
- `deletion_protection` must be strictly `true`.
- `recovery_window_in_days` must be >= 7.
- `0.0.0.0/0` prohibited in production security groups.
- `DATABASE_URL` injected via Secrets Manager ARN reference.
STATE TRANSITIONS: Declarative IaC provisioning states managed via remote Terraform state.

## Error contract

| Code | Trigger | HTTP/status | Retryable | Client-safe message | Audit | Metric |
|---|---|---|---:|---|---:|---|
| `IAC_POLICY_VIOLATION` | deletion_protection is false | N/A (CI failure) | no | Deletion protection must be enabled | yes | `iac_compliance_failures{rule="deletion_protection"}` |
| `IAC_POLICY_VIOLATION` | 0.0.0.0/0 present in production | N/A (CI failure) | no | Open 0.0.0.0/0 CIDR prohibited in production | yes | `iac_compliance_failures{rule="no_open_egress"}` |
| `IAC_POLICY_VIOLATION` | recovery_window is 0 | N/A (CI failure) | no | Secrets recovery window cannot be zero | yes | `iac_compliance_failures{rule="recovery_window"}` |
| `IAC_POLICY_VIOLATION` | Missing DATABASE_URL secret ref | N/A (CI failure) | no | ECS tasks must consume secrets from Secrets Manager | yes | `iac_compliance_failures{rule="secrets_injection"}` |

## Security contract

AUTHENTICATION: AWS IAM roles for ECS task execution and task runtime (`ecs_execution`, `ecs_task`).
AUTHORIZATION: Least-privilege IAM policies restricting Secrets Manager and KMS decrypt permissions.
TENANT: Infrastructure-level shared multi-tenant cluster with logically separated tenant schemas.
PII: PROHIBITED — no customer data in Terraform files or state outputs.
SECRET ACCESS: ECS tasks retrieve secrets via Secrets Manager ARN references; no plaintext secrets in environment variables.
EXTERNAL ACTION: Creation/modification of AWS cloud resources.
DEFAULT: DENY — default security group egress/ingress denied unless explicitly authorized.

## Specialized contracts

DATA CONTRACT: RDS Aurora PostgreSQL 16 cluster with Serverless v2 scaling, encrypted with customer-managed KMS key.
API CONTRACT: NOT APPLICABLE — Infrastructure manifest.
EVENT CONTRACT: CloudWatch container logs and EventBridge audit events.
TEMPORAL CONTRACT: Aurora automated backup retention: 7 days (staging), 35 days (production).
AGENT CONTRACT: NOT APPLICABLE.
MODEL CONTRACT: NOT APPLICABLE.
RAG CONTRACT: NOT APPLICABLE.

## Operational behavior

RETRY: Terraform resource reconciliation handles transient AWS API rate limits via provider retry logic.
TIMEOUT: Resource provisioning timeouts defined per resource block (e.g. 60m for RDS cluster).
IDEMPOTENCY: Terraform plan/apply operations are declarative and idempotent.
LOGGING: ECS container insights and CloudWatch log groups encrypted with KMS.
METRICS: Aurora and ECS metrics pushed to AWS CloudWatch.
FAILURE BEHAVIOR: Terraform state locks prevent concurrent applies; failed resources taint and require repair.
ROLLBACK/COMPENSATION: Terraform state rollback or destroy on unrecoverable syntax/infrastructure errors.

## Implementation requirements

1. In `infra/environments/staging/rds.tf`:
   - Update `deletion_protection = true`.
2. In `infra/environments/staging/secrets.tf`:
   - Change `recovery_window_in_days = 0` to `recovery_window_in_days = 7`.
3. In `infra/environments/staging/ecs.tf`:
   - In `aws_ecs_task_definition.api` and `aws_ecs_task_definition.workflow_worker`, add `secrets` block with `DATABASE_URL` pointing to `"${aws_secretsmanager_secret.platform_config.arn}:DATABASE_URL::"`.
4. In `infra/environments/staging/security_groups.tf`:
   - Replace broad outbound rules with specific private CIDR / gateway VPC endpoint rules.
5. Create `infra/environments/production/` and replicate the 10 core manifests from staging:
   - `alb.tf`, `ecs.tf`, `kms.tf`, `outputs.tf`, `rds.tf`, `secrets.tf`, `security_groups.tf`, `variables.tf`, `versions.tf`, `vpc.tf`.
6. Apply production-grade parameters across `infra/environments/production/`:
   - `environment = "production"`
   - `deletion_protection = true` in `rds.tf`
   - `backup_retention_period = 35` in `rds.tf`
   - `recovery_window_in_days = 30` in `secrets.tf`
   - `secrets` array with `DATABASE_URL` in `ecs.tf`
   - Restrict all security group ingress/egress rules: replace any `0.0.0.0/0` with CloudFront managed prefix lists, internal VPC CIDRs, or specific NAT gateway egress allowlists. Zero occurrences of `0.0.0.0/0` allowed in production files.
7. Run verification commands to ensure all acceptance criteria pass.

## Tests and evaluations

TESTS REQUIRED:
- Static analysis and grep evaluation across all Terraform files.
- Terraform syntax check / validation.

AI EVALS REQUIRED: NOT APPLICABLE.
PERFORMANCE REQUIREMENTS: NOT APPLICABLE.
MIGRATION REQUIREMENTS: Staging state compatibility preserved without resource recreation.

## Verification

COMMANDS:

```text
grep -rn "deletion_protection.*false" infra/environments/production/ || true && grep -rn "0.0.0.0/0" infra/environments/production/ || true && grep -rn "recovery_window.*=.*0" infra/environments/ || true && grep -rn "DATABASE_URL" infra/environments/staging/ecs.tf infra/environments/production/ecs.tf
```

EXPECTED:
- `grep -rn "deletion_protection.*false" infra/environments/production/` returns 0 matches.
- `grep -rn "0.0.0.0/0" infra/environments/production/` returns 0 matches.
- `grep -rn "recovery_window.*=.*0" infra/environments/` returns 0 matches.
- `grep -rn "DATABASE_URL" ...` returns matching secret references in both staging and production `ecs.tf`.

## Binary acceptance criteria

- `AC-AR-026-01`: PASS only if `grep -rn "deletion_protection.*false" infra/environments/production/` returns 0 matches.
- `AC-AR-026-02`: PASS only if `grep -rn "0.0.0.0/0" infra/environments/production/` returns 0 matches.
- `AC-AR-026-03`: PASS only if `grep -rn "recovery_window.*=.*0" infra/environments/` returns 0 matches.
- `AC-AR-026-04`: PASS only if ECS container definitions in both `infra/environments/staging/ecs.tf` and `infra/environments/production/ecs.tf` contain a `secrets` entry for `DATABASE_URL`.

## Postconditions

- Staging IaC updated with non-zero secret recovery window, deletion protection, and Secrets Manager injection.
- Complete production IaC established under `infra/environments/production/`.
- Production environment has zero open `0.0.0.0/0` rules.
- Production database deletion protection is permanently active.
- Automated static security invariants verifiable via non-destructive commands.

## Readiness score

| Dimension | 0–2 | Rationale |
|---|---:|---|
| Objective clarity | 2 | Clear objective: harden staging IaC and create production IaC |
| Dependency clarity | 2 | Upstream dependency: AR-027 |
| File boundary clarity | 2 | 4 modified staging files and 10 created production files |
| Contract clarity | 2 | Explicit requirements: deletion protection, recovery window, no 0.0.0.0/0, DATABASE_URL |
| Failure behavior | 2 | Fail closed: CI static checks reject non-compliant IaC |
| Security/tenancy | 2 | High-impact infrastructure security hardening (least privilege, network egress lock) |
| Testability | 1 | Verified statically via grep and terraform format/syntax checks without live cloud deploy |
| Verification | 1 | Offline static commands; live deployment requires AWS sandbox |
| Acceptance criteria | 2 | 4 concrete machine-verifiable grep criteria |
| Reasoning independence | 2 | Direct replication and hardening pattern with 0 new architectural decisions |

## Definition of done

All acceptance criteria pass; verification exits 0; no unexpected/prohibited files changed; no TODO/FIXME/placeholder/skipped test/fake pass; executor result matches the mandatory report format.

## Do not

- Retain `deletion_protection = false` in production RDS configuration.
- Introduce `0.0.0.0/0` in production security group ingress or egress rules.
- Set `recovery_window_in_days = 0` in any environment.
- Modify application or backend source code in `apps/` or `packages/`.

## Required executor report

```text
TASK TASK-AR-026 RESULT

STATUS: PASS | FAIL | BLOCKED
FILES CREATED: infra/environments/production/*.tf (10 files)
FILES MODIFIED: infra/environments/staging/{ecs.tf, rds.tf, secrets.tf, security_groups.tf}
UNEXPECTED FILES: NONE
TESTS: static IaC verification PASS
COMMANDS AND EXIT CODES: grep deletion_protection → 0, grep 0.0.0.0/0 → 0, grep recovery_window → 0, grep DATABASE_URL → 0
ACCEPTANCE: AC-AR-026-01: PASS|FAIL, AC-AR-026-02: PASS|FAIL, AC-AR-026-03: PASS|FAIL, AC-AR-026-04: PASS|FAIL
DEVIATIONS: NONE | <details>
NEXT TASK: NONE
```
