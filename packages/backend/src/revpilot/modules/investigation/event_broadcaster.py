"""
RevPilot AI — Asynchronous Multi-Tenant Investigation Event Broadcaster
Specification: docs/26-api/API-STANDARDS.md §6, docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md §6.2
Enforces INV-TEN-001 (tenant-isolated subscriber queues) and real-time SSE stream delivery.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator
import logging

logger = logging.getLogger("revpilot.investigation.broadcaster")


class InvestigationEventBroadcaster:
    """
    In-memory asynchronous pub/sub broadcaster distributing investigation lifecycle events
    to connected SSE clients. Subscriber queues are strictly partitioned by (tenant_id, investigation_id).
    """

    def __init__(self) -> None:
        # Key: (tenant_id, investigation_id) -> set of asyncio.Queue
        self._subscribers: dict[tuple[str, str], set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def publish(
        self,
        tenant_id: str,
        investigation_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Broadcast an event to all active subscribers of the given investigation.
        Returns the count of subscribers that received the event.
        """
        key = (str(tenant_id), str(investigation_id))
        event = {
            "event_type": event_type,
            "investigation_id": str(investigation_id),
            "tenant_id": str(tenant_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        async with self._lock:
            queues = list(self._subscribers.get(key, set()))

        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Queue full for subscriber on investigation %s:%s, dropping event",
                    tenant_id,
                    investigation_id,
                )

        return len(queues)

    async def subscribe(
        self,
        tenant_id: str,
        investigation_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Register a subscriber queue and yield incoming events until unsubscribed or cancelled.
        """
        key = (str(tenant_id), str(investigation_id))
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)

        async with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = set()
            self._subscribers[key].add(queue)

        try:
            while True:
                event = await queue.get()
                yield event
                queue.task_done()
        finally:
            async with self._lock:
                if key in self._subscribers and queue in self._subscribers[key]:
                    self._subscribers[key].remove(queue)
                    if not self._subscribers[key]:
                        del self._subscribers[key]

    async def get_subscriber_count(self, tenant_id: str, investigation_id: str) -> int:
        key = (str(tenant_id), str(investigation_id))
        async with self._lock:
            return len(self._subscribers.get(key, set()))
