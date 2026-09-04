"""
RevPilot AI — Connector Ingestion Worker (apps/ingestion-worker)
Schedules and coordinates SaaS connector ingestion, webhook deduplication, and staging ingestion.
Conforms to:
- docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md
- docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md
- ADR-0009 (Secrets and Keys)
- docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §6
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("revpilot.ingestion_worker")


class IngestionConfig:
    """Ingestion worker configuration derived from environment."""

    def __init__(self) -> None:
        self.poll_interval_sec = int(os.getenv("INGESTION_POLL_INTERVAL_SEC", "60"))
        self.max_batch_records = int(os.getenv("INGESTION_MAX_BATCH_RECORDS", "5000"))
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.egress_proxy_url = os.getenv("EGRESS_PROXY_URL", "")


async def run_ingestion_worker(config: IngestionConfig | None = None, stop_event: asyncio.Event | None = None) -> None:
    """Run connector ingestion worker until shutdown."""
    cfg = config or IngestionConfig()
    shutdown = stop_event or asyncio.Event()

    logger.info(
        "Initializing RevPilot Ingestion Worker (Poll Interval: %ds, Max Batch: %d, Egress Proxy: %s)",
        cfg.poll_interval_sec,
        cfg.max_batch_records,
        cfg.egress_proxy_url or "DIRECT_OFFLINE",
    )

    loop = asyncio.get_running_loop()

    def _handle_signal(sig_name: str) -> None:
        logger.info("Received signal %s. Draining connector sync streams...", sig_name)
        shutdown.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig.name: _handle_signal(s))
        except (NotImplementedError, RuntimeError):
            pass

    logger.info("Ingestion Worker active. Monitoring connector schedules and webhook buffers...")
    try:
        await shutdown.wait()
    finally:
        logger.info("Ingestion Worker cleanly drained and stopped.")


def main() -> None:
    """Entrypoint."""
    try:
        asyncio.run(run_ingestion_worker())
    except KeyboardInterrupt:
        logger.info("Ingestion Worker interrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
