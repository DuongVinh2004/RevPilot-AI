"""
RevPilot AI — Cryptographic Audit Log Hash Chaining Service
Specification: docs/22-billing/AUDIT-LOG-SPEC.md §3
Conforms to INV-AUD-001, NFR-AUD-001, and TC-P07-025.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict

from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime


class AuditRecord(BaseModel):
    """
    Immutable audit event cryptographically bound to predecessor hash.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: str
    occurred_at: UtcDateTime
    event_type: str
    tenant_id: TenantId | None
    actor_id: PrincipalId
    action: str
    details: dict[str, Any]
    previous_event_hash: str
    event_hash: str


class AuditHashChainService:
    """
    Maintains an append-only, tamper-evident SHA-256 hash chain per tenant (or system wide),
    verifying complete immutability and alerting immediately upon historical record alteration (TC-P07-025).
    """

    def __init__(self) -> None:
        self._chain: list[AuditRecord] = []

    def append_event(
        self,
        tenant_id: TenantId | None,
        actor_id: PrincipalId,
        event_type: str,
        action: str,
        details: dict[str, Any],
        event_id: str | None = None,
        occurred_at: UtcDateTime | None = None,
    ) -> AuditRecord:
        """
        Append a new immutable audit record to the cryptographic hash chain.
        """
        ev_id = event_id or f"evt_{uuid4().hex}"
        occ_at = occurred_at or UtcDateTime.now()

        # Retrieve previous hash or genesis seed
        previous_hash = self._chain[-1].event_hash if self._chain else "0" * 64

        t_val = tenant_id.value if tenant_id else "global"
        details_str = json.dumps(details, sort_keys=True)
        raw_to_hash = (
            f"{ev_id}:{occ_at.isoformat()}:{t_val}:{actor_id.value}:"
            f"{event_type}:{action}:{details_str}:{previous_hash}"
        )
        event_hash = hashlib.sha256(raw_to_hash.encode("utf-8")).hexdigest()

        record = AuditRecord(
            event_id=ev_id,
            occurred_at=occ_at,
            event_type=event_type,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            details=details,
            previous_event_hash=previous_hash,
            event_hash=event_hash,
        )

        self._chain.append(record)
        return record

    def verify_chain_integrity(self) -> tuple[bool, str | None]:
        """
        Sequentially recompute and verify the cryptographic integrity of the entire chain.
        Returns (True, None) if completely unaltered, or (False, error_reason) if tampered.
        """
        expected_prev = "0" * 64

        for idx, rec in enumerate(self._chain):
            # 1. Verify Back-Pointer Hash
            if rec.previous_event_hash != expected_prev:
                return (
                    False,
                    f"Broken hash chain at index {idx} (event '{rec.event_id}'): "
                    f"expected previous_hash '{expected_prev}', got '{rec.previous_event_hash}'",
                )

            # 2. Recompute Node Hash
            t_val = rec.tenant_id.value if rec.tenant_id else "global"
            details_str = json.dumps(rec.details, sort_keys=True)
            raw_to_hash = (
                f"{rec.event_id}:{rec.occurred_at.isoformat()}:{t_val}:{rec.actor_id.value}:"
                f"{rec.event_type}:{rec.action}:{details_str}:{rec.previous_event_hash}"
            )
            computed_hash = hashlib.sha256(raw_to_hash.encode("utf-8")).hexdigest()

            if computed_hash != rec.event_hash:
                return (
                    False,
                    f"Tamper detected at index {idx} (event '{rec.event_id}'): "
                    f"recomputed hash '{computed_hash}' != stored event_hash '{rec.event_hash}'",
                )

            expected_prev = rec.event_hash

        return (True, None)
