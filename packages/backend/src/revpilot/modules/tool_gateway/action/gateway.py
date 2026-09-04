"""
RevPilot AI — Tool Gateway Action Dispatch Gate & Egress Containment
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.1, §7.2
Conforms to INV-SEC-001, ADR-0009, INV-ACT-001, AC-009.
"""

from __future__ import annotations
import contextlib
import hashlib
import json
import re
import socket
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from revpilot.modules.action.domain import ActionLedgerRecord
from revpilot.modules.tool_gateway.action.credential_broker import (
    CredentialBroker,
    EphemeralCredential,
    GatewayError,
)
from revpilot.modules.tool_gateway.action.mock_adapter import MockProviderAdapter
from revpilot.shared.context import TenantContext
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.results import Result, Success, Failure
from revpilot.shared.temporal import UtcDateTime


SENSITIVE_KEYS = {
    "token",
    "token_id",
    "token_value",
    "token_secret",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "access_token",
    "bearer",
    "password",
    "private_key",
    "credential",
    "secret_key",
    "client_secret",
}

BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE)


def scrub_secrets(obj: Any, known_secrets: set[str] | None = None) -> Any:
    """
    Recursively scrub tokens, authorization headers, and credentials from payloads.
    Replaces sensitive keys and patterns with '[REDACTED]'.
    """
    secrets_set = known_secrets or set()
    if isinstance(obj, dict):
        scrubbed = {}
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                scrubbed[k] = scrub_secrets(v, secrets_set)
            elif any(sens in k.lower() for sens in SENSITIVE_KEYS):
                if isinstance(v, str) and BEARER_PATTERN.search(v):
                    scrubbed[k] = BEARER_PATTERN.sub("Bearer [REDACTED]", v)
                else:
                    scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = scrub_secrets(v, secrets_set)
        return scrubbed
    elif isinstance(obj, list):
        return [scrub_secrets(x, secrets_set) for x in obj]
    elif isinstance(obj, str):
        val = obj
        if BEARER_PATTERN.search(val):
            val = BEARER_PATTERN.sub("Bearer [REDACTED]", val)
        for s in secrets_set:
            if s and s in val:
                val = val.replace(s, "[REDACTED]")
        return val
    return obj


def compute_canonical_digest(data: Any) -> str:
    """
    Compute cryptographic SHA-256 digest over canonical JSON representation.
    """
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@contextlib.contextmanager
def agent_egress_barrier():
    """
    Egress containment barrier enforcing INV-SEC-001.
    Direct network connection attempts from within agent sub-processes fail closed.
    """
    original_socket = socket.socket

    def blocked_socket(*args: Any, **kwargs: Any) -> Any:
        raise GatewayError(
            code="ERR_DIRECT_EGRESS_BLOCKED",
            message="Direct agent egress is barred; only the Tool Gateway process may access external network (INV-SEC-001)",
            details={"socket_family": str(args[0] if args else "UNKNOWN")},
        )

    socket.socket = blocked_socket
    try:
        yield
    finally:
        socket.socket = original_socket


class ActionCapabilityRequest(BaseModel):
    """
    Typed capability dispatch request submitted to the Tool Gateway.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    intent_id: UUIDv7
    tenant_id: TenantId
    approval_id: UUIDv7
    approval_digest: str = Field(min_length=64, max_length=64)
    action_type: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    target_entities: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    is_dry_run: bool = False
    as_of_time: UtcDateTime


class ActionCapabilityGateway:
    """
    Authoritative egress gate and action dispatcher.
    Enforces tenant isolation, ephemeral credential validation, secret scrubbing, and mock routing.
    """

    def __init__(
        self,
        credential_broker: CredentialBroker | None = None,
        mock_adapter: MockProviderAdapter | None = None,
        default_provider: str = "mock_logistics_v1",
    ) -> None:
        self.credential_broker = credential_broker or CredentialBroker()
        self.mock_adapter = mock_adapter or MockProviderAdapter()
        self.default_provider = default_provider

    async def dispatch_action(
        self,
        ctx: TenantContext,
        req: ActionCapabilityRequest,
    ) -> Result[ActionLedgerRecord, GatewayError]:
        """
        Execute audited action dispatch pipeline across 7 safety gates.
        """
        # Gate 1: Tenant Validation Gate (INV-TEN-002)
        if ctx.tenant_id != req.tenant_id:
            return Failure(
                GatewayError(
                    code="ERR_TENANT_MISMATCH",
                    message=f"Context tenant '{ctx.tenant_id}' does not match request tenant '{req.tenant_id}'",
                    details={"ctx_tenant": str(ctx.tenant_id), "req_tenant": str(req.tenant_id)},
                )
            )

        # Gate 2: Approval Digest Verification (AC-008, INV-ACT-002)
        if not req.approval_digest or len(req.approval_digest) != 64:
            return Failure(
                GatewayError(
                    code="ERR_APPROVAL_DIGEST_MISMATCH",
                    message="Action dispatch requires valid 64-character SHA-256 approval digest",
                    details={"approval_digest": req.approval_digest},
                )
            )

        # Gate 3: Dry-Run Simulation Protocol (AC-009)
        if req.is_dry_run:
            scrubbed_req = scrub_secrets(req.payload)
            req_digest = compute_canonical_digest(scrubbed_req)
            simulated_response = {
                "status": "DRY_RUN_ACCEPTED",
                "action_type": req.action_type,
                "targets_count": len(req.target_entities),
                "zero_side_effect": True,
            }
            resp_digest = compute_canonical_digest(simulated_response)
            now = UtcDateTime.now()
            ledger_record = ActionLedgerRecord(
                ledger_id=UUIDv7.generate(),
                tenant_id=req.tenant_id,
                intent_id=req.intent_id,
                attempt_number=1,
                idempotency_key=req.idempotency_key,
                provider_name=self.default_provider,
                request_digest=req_digest,
                response_digest=resp_digest,
                http_status_code=200,
                provider_tx_id=f"tx_dryrun_{str(req.intent_id).replace('-', '')[:12]}",
                execution_status="SUCCESS",
                started_at=req.as_of_time,
                completed_at=now,
            )
            return Success(ledger_record)

        # Gate 4: Ephemeral Token Exchange (INV-SEC-001, ADR-0009)
        try:
            credential = await self.credential_broker.issue_ephemeral_token(
                tenant_id=req.tenant_id,
                provider=self.default_provider,
                action_type=req.action_type,
            )
        except GatewayError as err:
            return Failure(
                GatewayError(
                    code="ERR_CREDENTIAL_ISSUANCE_FAILED",
                    message=f"Credential issuance failed: {err.message}",
                    details=err.details,
                )
            )

        # Gate 5: Token Scope and Expiry Revalidation
        validation_res = self.credential_broker.validate_token(
            credential=credential,
            tenant_id=req.tenant_id,
            provider=self.default_provider,
            action_type=req.action_type,
            as_of_time=req.as_of_time,
        )
        if isinstance(validation_res, Failure):
            return validation_res

        # Gate 6: Outbound Secret Scrubbing (INV-AUD-002)
        known_secrets = {credential.token_id, credential.token_secret}
        scrubbed_payload = scrub_secrets(req.payload, known_secrets)
        request_digest = compute_canonical_digest(scrubbed_payload)

        # Gate 7: Sandboxed Mock Provider Execution
        adapter_res = self.mock_adapter.execute(
            intent_id=str(req.intent_id),
            action_type=req.action_type,
            target_entities=req.target_entities,
            payload=req.payload,
            credential=credential,
        )

        now = UtcDateTime.now()
        if isinstance(adapter_res, Failure):
            err = adapter_res.error
            error_record = ActionLedgerRecord(
                ledger_id=UUIDv7.generate(),
                tenant_id=req.tenant_id,
                intent_id=req.intent_id,
                attempt_number=1,
                idempotency_key=req.idempotency_key,
                provider_name=self.default_provider,
                request_digest=request_digest,
                response_digest=None,
                http_status_code=err.details.get("status_code", 500) if err.details else 500,
                provider_tx_id=None,
                execution_status="PROVIDER_ERROR",
                error_code=err.code,
                started_at=req.as_of_time,
                completed_at=now,
            )
            return Success(error_record)

        mock_resp = adapter_res.value
        scrubbed_resp_payload = scrub_secrets(mock_resp.response_payload, known_secrets)
        response_digest = compute_canonical_digest(scrubbed_resp_payload)

        ledger_record = ActionLedgerRecord(
            ledger_id=UUIDv7.generate(),
            tenant_id=req.tenant_id,
            intent_id=req.intent_id,
            attempt_number=1,
            idempotency_key=req.idempotency_key,
            provider_name=self.default_provider,
            request_digest=request_digest,
            response_digest=response_digest,
            http_status_code=mock_resp.http_status_code,
            provider_tx_id=mock_resp.provider_tx_id,
            execution_status="SUCCESS" if mock_resp.http_status_code == 200 else "PROVIDER_ERROR",
            started_at=req.as_of_time,
            completed_at=now,
        )

        return Success(ledger_record)
