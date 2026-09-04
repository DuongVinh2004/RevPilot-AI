# Tool Gateway and Action Safety Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 03 — Governed Evidence and Investigation (Rails 6, 15)
Owner: Security Architecture / Platform Architecture
Traceability: `INV-ACT-001..004`, `INV-SEC-001..003`, `INV-IAM-001..002`, `INV-REL-001`, `SEC-001..004`, `NFR-SEC-001`, `NFR-DUR-001`, `AC-008`, `AC-009`, `ADR-0003`, `ADR-0009`

---

## 1. Tool Gateway Architecture and Core Invariants

The **Tool Gateway** is the single authoritative egress boundary between RevPilot AI core execution and data or enterprise tools. No agent, workflow activity, or background service may perform network I/O or database access without passing through the Tool Gateway.

### Core Invariants:
1. **Zero Direct Agent Tool Access (`INV-SEC-001`, `SEC-002`)**: Agents never execute code or call remote APIs directly. Agents emit typed `CapabilityRequest` objects; the Tool Gateway validates and executes them.
2. **Phase 03 Strict Read-Only Boundary (`INV-ACT-001`)**: All mutation and external action adapters are disabled in Phase 03. Only registered read-only data capabilities (`SQL_READ`, `DOCUMENT_RETRIEVE`, `TICKET_INGEST`) are active.
3. **Server-Side Authorization and Delegation (`INV-IAM-001..002`, `SEC-003`)**: Every capability request requires a valid `TenantContext` and `PrincipalContext`. Delegated agent authority cannot exceed the human principal's rights.
4. **Registered Capability Whitelist (`INV-SEC-003`)**: Tool schemas, parameter types, database projection lists, and destination endpoints are statically registered and versioned. Arbitrary destination routing or untyped execution is rejected.

---

## 2. Phase 03 Capability Gateway Interface

In Phase 03, the Tool Gateway exposes the `ReadOnlyCapabilityPort`:

```python
class CapabilityType(str, Enum):
    SQL_READ = "SQL_READ"
    RETRIEVAL = "RETRIEVAL"
    TICKET_READ = "TICKET_READ"

class ToolCapabilityDefinition(BaseModel):
    capability_id: str
    capability_type: CapabilityType
    version: str
    required_permission: str
    max_timeout_ms: int
    rate_limit_per_minute: int
    data_classification: ClassificationLevel
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

class IReadOnlyCapabilityGateway(ABC):
    @abstractmethod
    async def execute_capability(
        self,
        request: CapabilityRequest
    ) -> Result[CapabilityResult, GatewayError]:
        """Validates tenancy, authorization, budgets, executes capability, and attaches audit."""
        pass
```

---

## 3. Dispatch Pipeline and Safety Checks

Every capability invocation passes through 6 mandatory gates:

```text
 [CapabilityRequest]
         │
         ▼
 [1. Tenant Validation Gate] ──(Missing / Forged)──► FAIL CLOSED (HTTP 403)
         │
         ▼
 [2. RBAC/ABAC Gate] ─────────(Missing Perm)───────► FAIL CLOSED (HTTP 403)
         │
         ▼
 [3. Registry & Schema Gate] ──(Unregistered)──────► REJECT (ERR_UNREGISTERED_TOOL)
         │
         ▼
 [4. FinOps Budget Gate] ─────(Budget Breached)────► HALT (ERR_BUDGET_EXCEEDED)
         │
         ▼
 [5. Read-Only Policy Gate] ──(Mutation Attempt)───► HALT & ALERT (ERR_MUTATION_BLOCKED)
         │
         ▼
 [6. Sandboxed Execution] ────(DB / Vector Store)──► Sealed CapabilityResult
```

### Gate Rules:
1. **Tenant Validation Gate**: Ensures `request.tenant_context.tenant_id` matches the session. Rejects forged tenant tokens (`INV-TEN-002`).
2. **RBAC/ABAC Gate**: Evaluates `PrincipalContext` against `ToolCapabilityDefinition.required_permission`.
3. **Registry & Schema Gate**: Validates input parameters against registered Pydantic schemas. Strips unknown parameters.
4. **FinOps Budget Gate**: Checks investigation budget ledger (`INV-COST-001`). If USD spend or tool call limit is reached, execution is denied.
5. **Read-Only Policy Gate**: Verifies capability is in the read-only catalog (`SQL-CAPABILITY-CATALOG.md`). Rejects any write or mutation intent.
6. **Sandboxed Execution**: Executes query using read-only database connections (`revpilot_app_readonly`) with strict statement timeouts (max 5,000ms).

---

## 4. Mutation and Side-Effect Barrier (Phase 03)

In Phase 03, action execution capabilities (Email, CRM update, ERP refund, Slack notify) are structurally blocked:
- Action adapters exist only as interface definitions or mock/dry-run stubs (`ADR-0003`).
- Invocation of any action adapter throws `ActionExecutionBlockedError: Phase 03 is read-only`.
- The `ActionLedger` records attempt as `REJECTED_PHASE_GATE` and triggers security alert `security.tool_gateway.unauthorized_mutation_attempt`.

---

## 5. Audit, Observability, and Telemetry

Under `INV-AUD-001` and `NFR-OBS-001`:
1. Every capability execution emits a structured audit record:
   - `tenant_id`
   - `investigation_id`
   - `capability_id`
   - `principal_id`
   - `query_digest` (SHA-256)
   - `execution_duration_ms`
   - `row_count` or `chunk_count`
   - `authorization_decision`: `PERMITTED` or `DENIED`
2. Raw payloads containing PII or secrets are NEVER written to logs or audit records (`INV-AUD-002`, `INV-PRV-001`).

---

## 6. Verification and Test Suite Mapping

- `tests/security/test_tool_gateway_tenancy.py`: Verifies capability execution fails closed if tenant context is altered or missing (`INV-TEN-002`).
- `tests/security/test_tool_gateway_mutation_barrier.py`: Attempts to execute action/mutation capabilities; verifies 100% rejection and security alerts (`INV-ACT-001`).
- `tests/security/test_tool_gateway_budget_enforcement.py`: Tests that exceeding investigation USD budget halts capability execution (`INV-COST-001`).
- `tests/contract/test_tool_capability_schema_enforcement.py`: Tests that invalid input schemas are rejected before execution.

---

## 7. Phase 06 Action Dispatch, Credential Broker, Dry-Run, and Safety Controls

### 7.1. Action Capability Port (`IActionCapabilityGateway`)
In Phase 06, the Tool Gateway exposes controlled write capabilities governed by cryptographic approval binding (`AC-008`):

```python
class ActionCapabilityRequest(BaseModel):
    intent_id: UUIDv7
    tenant_id: TenantId
    approval_id: UUIDv7
    approval_digest: str
    action_type: str
    idempotency_key: str
    target_entities: List[str]
    payload: Dict[str, Any]
    is_dry_run: bool = False
    as_of_time: UtcDateTime

class IActionCapabilityGateway(ABC):
    @abstractmethod
    async def execute_action(
        self,
        request: ActionCapabilityRequest
    ) -> Result[ActionLedgerRecord, GatewayError]:
        """Validates approval digest, revalidates policy, checks kill switches, issues credentials, and dispatches action."""
        pass
```

### 7.2. Credential Broker Boundary (`INV-SEC-001`, `ADR-0009`)
1. **Short-Lived Ephemeral Tokens**: The gateway delegates external authentication to an internal Credential Broker. Tokens are issued with a maximum 15-minute TTL bound to the specific `tenant_id` and `action_type`.
2. **Zero Secret Leakage**: AI agents, workflow task histories, and database ledger records NEVER store raw API keys, bearer tokens, or client secrets.
3. **No Direct Agent Egress**: Network firewalls and VPC egress rules physically restrict outbound external traffic to the Tool Gateway process only.

### 7.3. Dry-Run Simulation Protocol (`AC-009`)
- When `is_dry_run = True`, the Tool Gateway runs identical tenant validation, schema checks, policy rules, budget calculations, and blast radius verifications.
- It intercepts the provider invocation, returns simulated responses and estimated costs, records a dry-run audit event, and physically prohibits external socket connection.

### 7.4. Multi-Tier Kill Switch Integration
Before dispatching any outbound network byte, the gateway evaluates the distributed kill switch cache. If any kill switch matching global, tenant, capability, provider, or investigation scope is `ACTIVE`, the action aborts immediately with `ERR_KILL_SWITCH_ACTIVE` within $< 500\text{ms}$.
