"""
RevPilot AI — Chaos Engineering & Fault Injection Engine
Specification: docs/29-testing/TEST-STRATEGY.md §13.2
Conforms to INV-REL-001, NFR-AVL-001, and TC-P08-005.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class FaultInjector:
    """
    Fault injection coordinator for synthetic load and resilience testing.
    Allows injecting controlled network latency, socket blackholing, and worker SIGKILL simulation.
    All injected faults are fully reversible via clear_all_faults().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._network_latency: dict[str, int] = {}
        self._socket_blackholes: set[str] = set()
        self._killed_workers: set[int] = set()

    def inject_network_latency(self, target_service: str, latency_ms: int) -> None:
        """Inject synthetic network latency for a target downstream service."""
        with self._lock:
            self._network_latency[target_service] = max(0, latency_ms)
            logger.info("Fault injected: latency %dms on service %s", latency_ms, target_service)

    def inject_socket_blackhole(self, target_service: str) -> None:
        """Inject full socket packet drop / blackhole for a target service."""
        with self._lock:
            self._socket_blackholes.add(target_service)
            logger.warning("Fault injected: socket blackhole on service %s", target_service)

    def inject_worker_sigkill(self, worker_process_id: int) -> None:
        """Simulate SIGKILL (signal 9 ungraceful termination) on worker process."""
        with self._lock:
            self._killed_workers.add(worker_process_id)
            logger.warning("Fault injected: SIGKILL on worker %d", worker_process_id)

    def is_service_blackholed(self, target_service: str) -> bool:
        """Check if target service currently experiences socket blackhole."""
        with self._lock:
            return target_service in self._socket_blackholes

    def get_service_latency_ms(self, target_service: str) -> int:
        """Get currently configured latency injection for service, or 0 if none."""
        with self._lock:
            return self._network_latency.get(target_service, 0)

    def is_worker_killed(self, worker_process_id: int) -> bool:
        """Check if worker process was terminated via SIGKILL simulation."""
        with self._lock:
            return worker_process_id in self._killed_workers

    def get_active_faults(self) -> dict[str, Any]:
        """Return snapshot of all currently active injected faults."""
        with self._lock:
            return {
                "network_latency": dict(self._network_latency),
                "socket_blackholes": sorted(list(self._socket_blackholes)),
                "killed_workers": sorted(list(self._killed_workers)),
            }

    def clear_all_faults(self) -> None:
        """Tear down all synthetic fault injection rules, restoring clean state."""
        with self._lock:
            self._network_latency.clear()
            self._socket_blackholes.clear()
            self._killed_workers.clear()
            logger.info("All injected faults cleared successfully.")
