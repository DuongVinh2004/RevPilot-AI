"""
RevPilot AI — Multi-Tenant Quota & Atomic Spend Reservation Manager
Specification: docs/21-finops/FINOPS-SPEC.md §2, DATABASE-SCHEMA.md §21.6
Conforms to INV-COST-001, NFR-COST-001, and TC-P07-022.
"""

from __future__ import annotations

from decimal import Decimal
import threading
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime


class QuotaError(Exception):
    """Base exception for FinOps and quota operations."""
    def __init__(self, message: str, code: str = "QUOTA_ERROR", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class QuotaExhaustedError(QuotaError):
    def __init__(self, message: str = "Tenant quota exceeded") -> None:
        super().__init__(message=message, code="QUOTA_EXHAUSTED", status_code=402)


class ReservationExpiredError(QuotaError):
    def __init__(self, message: str = "Reservation token expired") -> None:
        super().__init__(message=message, code="RESERVATION_EXPIRED", status_code=409)


class SpendReservationToken(BaseModel):
    """
    Time-bounded spend pre-authorization token ensuring zero unallocated spend.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    token_id: str
    tenant_id: TenantId
    reserved_amount: Decimal
    dimension: str
    expires_at: UtcDateTime
    is_finalized: bool = False
    is_released: bool = False
    created_at: UtcDateTime


class TenantQuotaPolicy(BaseModel):
    """
    Budget and concurrency limits allocated to a tenant.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tenant_id: TenantId
    hard_spend_limit_usd: Decimal
    reserved_spend_usd: Decimal = Field(default_factory=lambda: Decimal("0.00"))
    committed_spend_usd: Decimal = Field(default_factory=lambda: Decimal("0.00"))
    dimension_limits: dict[str, int | Decimal] = Field(default_factory=dict)
    current_dimension_usage: dict[str, int | Decimal] = Field(default_factory=dict)


class QuotaManager:
    """
    Authoritative FinOps manager executing thread-safe, atomic spend reservations,
    preventing over-allocation during high-concurrency races (INV-COST-001).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._policies: dict[str, TenantQuotaPolicy] = {}
        self._reservations: dict[str, SpendReservationToken] = {}

    def set_quota_policy(
        self,
        tenant_id: TenantId,
        hard_spend_limit_usd: Decimal,
        dimension_limits: dict[str, int | Decimal] | None = None,
    ) -> TenantQuotaPolicy:
        """Initialize or update tenant quota policy."""
        with self._lock:
            policy = TenantQuotaPolicy(
                tenant_id=tenant_id,
                hard_spend_limit_usd=hard_spend_limit_usd,
                dimension_limits=dimension_limits or {},
            )
            self._policies[tenant_id.value] = policy
            return policy

    def get_quota_policy(self, tenant_id: TenantId) -> TenantQuotaPolicy:
        """Fetch policy or create default pilot policy."""
        with self._lock:
            policy = self._policies.get(tenant_id.value)
            if not policy:
                # Default pilot policy: $1000.00 hard limit
                policy = self.set_quota_policy(tenant_id, hard_spend_limit_usd=Decimal("1000.00"))
            return policy

    def reserve_spend(
        self,
        tenant_id: TenantId,
        estimated_usd: Decimal,
        dimension: str = "spend_usd",
        ttl_seconds: int = 60,
        as_of_time: UtcDateTime | None = None,
    ) -> SpendReservationToken:
        """
        Atomically reserve estimated spend against remaining budget.
        Rejects concurrent attempts when remaining budget is insufficient (TC-P07-022).
        """
        if estimated_usd <= Decimal("0.00"):
            raise ValueError("Estimated spend must be strictly positive")

        with self._lock:
            policy = self.get_quota_policy(tenant_id)
            available = policy.hard_spend_limit_usd - (policy.reserved_spend_usd + policy.committed_spend_usd)

            if available < estimated_usd:
                raise QuotaExhaustedError(
                    f"Tenant '{tenant_id.value}' spend quota exhausted: requested ${estimated_usd}, available ${available:.2f} (Limit: ${policy.hard_spend_limit_usd})"
                )

            # Atomically reserve funds
            policy.reserved_spend_usd += estimated_usd

            now = as_of_time or UtcDateTime.now()
            expires_at = UtcDateTime.from_iso(
                (now.value + threading.Event().__class__ and (now.value)).isoformat()
            ) if False else UtcDateTime(now.value + (now.value.tzinfo and __import__("datetime").timedelta(seconds=ttl_seconds)))

            token_id = f"res_{uuid4().hex}"
            token = SpendReservationToken(
                token_id=token_id,
                tenant_id=tenant_id,
                reserved_amount=estimated_usd,
                dimension=dimension,
                expires_at=expires_at,
                created_at=now,
            )
            self._reservations[token_id] = token
            return token

    def finalize_spend(
        self,
        token: SpendReservationToken,
        actual_usd: Decimal,
        as_of_time: UtcDateTime | None = None,
    ) -> None:
        """
        Finalize spend: deduct actual amount from remaining budget and release unused reserved funds.
        """
        with self._lock:
            stored_token = self._reservations.get(token.token_id)
            if not stored_token:
                raise ValueError(f"Reservation token '{token.token_id}' not found")
            if stored_token.is_finalized:
                return  # Idempotent
            if stored_token.is_released:
                raise ValueError("Reservation token has already been released")

            now = as_of_time or UtcDateTime.now()
            if now.value.timestamp() > stored_token.expires_at.value.timestamp():
                # Expired reservation
                policy = self.get_quota_policy(stored_token.tenant_id)
                policy.reserved_spend_usd -= stored_token.reserved_amount
                stored_token.is_released = True
                raise ReservationExpiredError(f"Reservation token '{token.token_id}' expired before finalization")

            policy = self.get_quota_policy(stored_token.tenant_id)
            # Release reserved amount and commit actual
            policy.reserved_spend_usd -= stored_token.reserved_amount
            policy.committed_spend_usd += actual_usd
            stored_token.is_finalized = True

    def release_reservation(self, token: SpendReservationToken) -> None:
        """Release unused reservation without committing spend."""
        with self._lock:
            stored_token = self._reservations.get(token.token_id)
            if not stored_token or stored_token.is_finalized or stored_token.is_released:
                return
            policy = self.get_quota_policy(stored_token.tenant_id)
            policy.reserved_spend_usd -= stored_token.reserved_amount
            stored_token.is_released = True

    def check_rate_limit(self, tenant_id: TenantId, dimension: str, requested: int = 1) -> bool:
        """Thread-safe rate and volume check."""
        with self._lock:
            policy = self.get_quota_policy(tenant_id)
            limit = policy.dimension_limits.get(dimension)
            if limit is None:
                return True  # Unbounded

            current = policy.current_dimension_usage.get(dimension, 0)
            if current + requested > limit:
                return False

            policy.current_dimension_usage[dimension] = current + requested
            return True
