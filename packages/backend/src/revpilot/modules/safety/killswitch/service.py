"""
RevPilot AI — Safety Kill Switch Service & Distributed State Propagation
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §5
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.4
Conforms to INV-REL-001, INV-ACT-003, and NFR-COST-001.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Callable, Optional

from revpilot.modules.safety.killswitch.domain import (
    AgentOverrideForbiddenError,
    KillSwitchActiveError,
    KillSwitchError,
    KillSwitchRecord,
    KillSwitchScope,
)
from revpilot.shared.identifiers import TenantId, UUIDv7
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


def is_agent_identifier(principal: str) -> bool:
    """
    Check whether a principal string denotes an automated AI agent or bot.
    AI agents are strictly prohibited from manipulating kill switches.
    """
    p = principal.strip().lower()
    return (
        "agent" in p
        or "bot" in p
        or p.startswith("usr_agent")
        or p.startswith("usr_bot")
        or p == "agent_delegate"
    )


class DistributedKillSwitchBus:
    """
    Shared distributed transport simulating Redis pub/sub or clustered state sync.
    Enforces INV-REL-001 (< 500ms propagation across all gateway nodes).
    """

    def __init__(self) -> None:
        self._subscribers: list[Callable[[KillSwitchRecord], None]] = []
        self._active_records: dict[str, KillSwitchRecord] = {}
        self.is_healthy: bool = True

    def register_subscriber(self, callback: Callable[[KillSwitchRecord], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, record: KillSwitchRecord) -> None:
        if not self.is_healthy:
            raise ConnectionError("Distributed cache connection unreachable")
        self._active_records[str(record.switch_id)] = record
        for cb in self._subscribers:
            try:
                cb(record)
            except Exception as exc:
                logger.warning("Subscriber callback error during kill switch propagation: %s", exc)

    def get_all(self) -> list[KillSwitchRecord]:
        if not self.is_healthy:
            raise ConnectionError("Distributed cache connection unreachable")
        return list(self._active_records.values())


_GLOBAL_BUS = DistributedKillSwitchBus()


class KillSwitchService:
    """
    Multi-tier safety kill switch manager with rapid cache sync and fail-closed guarantees.
    Evaluated synchronously at Tool Gateway before network socket transmission.
    """

    def __init__(
        self,
        bus: DistributedKillSwitchBus | None = None,
        enable_db_fallback: bool = True,
    ) -> None:
        self._bus = bus if bus is not None else _GLOBAL_BUS
        self._local_cache: dict[str, KillSwitchRecord] = {}
        self._db_store: dict[str, KillSwitchRecord] = {}
        self._enable_db_fallback = enable_db_fallback
        self.is_db_healthy: bool = True

        # Subscribe to distributed propagation updates
        self._bus.register_subscriber(self._on_remote_update)

        # Seed local cache from shared bus if reachable
        try:
            for record in self._bus.get_all():
                self._local_cache[str(record.switch_id)] = record
                self._db_store[str(record.switch_id)] = record
        except ConnectionError:
            pass

    def _on_remote_update(self, record: KillSwitchRecord) -> None:
        """Receive instant push notification of switch activation/deactivation."""
        self._local_cache[str(record.switch_id)] = record
        self._db_store[str(record.switch_id)] = record

    async def activate(
        self,
        scope: KillSwitchScope,
        target_id: Optional[str],
        reason: str,
        principal: str,
    ) -> KillSwitchRecord:
        """
        Activate a kill switch across specified scope.
        Guarantees fail-closed enforcement and AI agent rejection (INV-ACT-003).
        """
        if is_agent_identifier(principal):
            raise AgentOverrideForbiddenError(
                f"Principal '{principal}' is an AI agent. AI agents cannot activate or deactivate kill switches.",
                details={"principal": principal, "scope": scope.value},
            )

        switch_id = UUIDv7.generate()
        now = UtcDateTime.now()
        normalized_target = target_id.strip() if target_id else None

        record = KillSwitchRecord(
            switch_id=switch_id,
            scope=scope,
            target_id=normalized_target,
            is_active=True,
            reason=reason.strip(),
            activated_by=principal.strip(),
            activated_at=now,
        )

        # 1. Write to DB store
        if self.is_db_healthy:
            self._db_store[str(switch_id)] = record

        # 2. Update local cache
        self._local_cache[str(switch_id)] = record

        # 3. Publish to distributed bus (< 500ms propagation)
        try:
            self._bus.publish(record)
        except ConnectionError as exc:
            logger.warning("Failed to publish to distributed cache: %s", exc)

        return record

    async def deactivate(
        self,
        switch_id: UUIDv7,
        reason: str,
        principal: str,
    ) -> KillSwitchRecord:
        """
        Deactivate an existing kill switch. Strictly forbidden for AI agents (INV-ACT-003).
        """
        if is_agent_identifier(principal):
            raise AgentOverrideForbiddenError(
                f"Principal '{principal}' is an AI agent. AI agents cannot deactivate kill switches.",
                details={"principal": principal, "switch_id": str(switch_id)},
            )

        sid_str = str(switch_id)
        existing = self._local_cache.get(sid_str) or self._db_store.get(sid_str)
        if not existing:
            raise KillSwitchError(f"Kill switch '{switch_id}' not found", details={"switch_id": sid_str})

        now = UtcDateTime.now()
        updated = KillSwitchRecord(
            switch_id=existing.switch_id,
            scope=existing.scope,
            target_id=existing.target_id,
            is_active=False,
            reason=reason.strip(),
            activated_by=existing.activated_by,
            activated_at=existing.activated_at,
            deactivated_by=principal.strip(),
            deactivated_at=now,
        )

        if self.is_db_healthy:
            self._db_store[sid_str] = updated
        self._local_cache[sid_str] = updated

        try:
            self._bus.publish(updated)
        except ConnectionError as exc:
            logger.warning("Failed to publish deactivation to distributed cache: %s", exc)

        return updated

    async def get_active_switches(self) -> list[KillSwitchRecord]:
        """
        Retrieve all currently active kill switches with fail-closed fallback.
        """
        # Try distributed cache first
        try:
            records = self._bus.get_all()
            return [r for r in records if r.is_active]
        except ConnectionError:
            pass

        # Fallback to local memory / database
        if self.is_db_healthy:
            return [r for r in self._db_store.values() if r.is_active]

        # Fail closed: if both cache and DB are dead, indicate system is in emergency lock
        logger.error("Fail-closed: Both distributed cache and database are unreachable")
        return [
            KillSwitchRecord(
                switch_id=UUIDv7.generate(),
                scope=KillSwitchScope.GLOBAL,
                target_id="*",
                is_active=True,
                reason="FAIL_CLOSED_SYSTEM_STORE_UNREACHABLE",
                activated_by="system_safety_guard",
                activated_at=UtcDateTime.now(),
            )
        ]

    async def is_blocked(
        self,
        tenant_id: TenantId,
        capability: str,
        provider: str,
        investigation_id: Optional[UUIDv7] = None,
    ) -> bool:
        """
        Evaluate if an action is blocked by any matching multi-tier kill switch.
        Scopes evaluated:
          1. GLOBAL
          2. TENANT (target_id == tenant_id)
          3. CAPABILITY (target_id == capability)
          4. PROVIDER (target_id == provider)
          5. INVESTIGATION (target_id == investigation_id)

        Fail-closed invariant: If cache and DB are both down, returns True.
        """
        active_switches = await self.get_active_switches()

        tnt_str = str(tenant_id)
        cap_str = capability.strip().lower()
        prv_str = provider.strip().lower()
        inv_str = str(investigation_id).strip().lower() if investigation_id else None

        for switch in active_switches:
            if not switch.is_active:
                continue

            # Tier 1: Global Platform
            if switch.scope == KillSwitchScope.GLOBAL:
                return True

            target = switch.target_id.strip() if switch.target_id else ""
            target_lower = target.lower()

            # Tier 2: Tenant Level
            if switch.scope == KillSwitchScope.TENANT:
                if target == tnt_str or target_lower == tnt_str.lower():
                    return True

            # Tier 3: Capability / Tool Level
            elif switch.scope == KillSwitchScope.CAPABILITY:
                if target_lower == cap_str:
                    return True

            # Tier 4: Provider Level
            elif switch.scope == KillSwitchScope.PROVIDER:
                if target_lower == prv_str:
                    return True

            # Tier 5: Investigation Level
            elif switch.scope == KillSwitchScope.INVESTIGATION:
                if inv_str and (target == str(investigation_id) or target_lower == inv_str):
                    return True

        return False
