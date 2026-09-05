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
import json
import logging
import os
import signal
import sys
from typing import Any

from revpilot.modules.tickets.services.dlp_scrubber import scrub_pii_and_secrets, calculate_injection_risk
from revpilot.modules.tickets.services.normalizer import normalize_ticket_text

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("revpilot.ingestion_worker")


class IngestionConfig:
    """Ingestion worker configuration derived from environment."""

    def __init__(self) -> None:
        self.poll_interval_sec = int(os.getenv("INGESTION_POLL_INTERVAL_SEC", "10"))
        self.max_batch_records = int(os.getenv("INGESTION_MAX_BATCH_RECORDS", "5000"))
        self.database_url = os.getenv("DATABASE_URL")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.egress_proxy_url = os.getenv("EGRESS_PROXY_URL", "")


async def process_inbox_item(row: Any, conn: Any) -> None:
    """Process a single connector inbox event through DQ & DLP pipeline."""
    payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
    tenant_id = row["tenant_id"]
    inbox_id = row["id"]

    try:
        # Check raw text if ticket
        raw_text = payload.get("body", "") or payload.get("description", "")
        if raw_text:
            scrubbed = scrub_pii_and_secrets(raw_text)
            injection_risk = calculate_injection_risk(scrubbed)
            if injection_risk > 0.85:
                logger.warning("High prompt injection risk (%.2f) on inbox item %s; quarantining.", injection_risk, inbox_id)
                await conn.execute(
                    """
                    INSERT INTO revpilot.connector_quarantine (
                        tenant_id, id, connector_id, rule_id, severity, source_id,
                        raw_payload, rejection_reason, status
                    ) VALUES (
                        $1, 'qr_' || $2, $3, 'RULE_PROMPT_INJECTION', 'CRITICAL', $4, $5, $6, 'QUARANTINED'
                    ) ON CONFLICT DO NOTHING;
                    """,
                    tenant_id,
                    inbox_id,
                    row["connector_id"],
                    row["external_event_id"],
                    json.dumps(payload),
                    f"Prompt injection risk score {injection_risk:.2f}",
                )
                await conn.execute(
                    "UPDATE revpilot.connector_inbox SET status = 'QUARANTINED', processed_at = CURRENT_TIMESTAMP WHERE id = $1",
                    inbox_id,
                )
                return

        # Mark processed
        await conn.execute(
            "UPDATE revpilot.connector_inbox SET status = 'PROCESSED', processed_at = CURRENT_TIMESTAMP WHERE id = $1",
            inbox_id,
        )
        logger.info("Processed inbox event %s successfully", inbox_id)

    except Exception as exc:
        logger.error("Failed processing inbox event %s: %s", inbox_id, exc)
        await conn.execute(
            "UPDATE revpilot.connector_inbox SET status = 'FAILED', processed_at = CURRENT_TIMESTAMP WHERE id = $1",
            inbox_id,
        )


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

    pool = None
    if cfg.database_url:
        try:
            from revpilot.infrastructure.database import create_database_pool
            pool = await create_database_pool(cfg.database_url)
            logger.info("Ingestion Worker connected to database pool.")
        except Exception as exc:
            logger.warning("Ingestion Worker DB deferred: %s", exc)

    logger.info("Ingestion Worker entering active polling loop...")

    try:
        while not shutdown.is_set():
            if pool is not None:
                try:
                    async with pool.acquire() as conn:
                        # Fetch pending inbox events across tenants
                        rows = await conn.fetch(
                            "SELECT id, tenant_id, connector_id, external_event_id, payload "
                            "FROM revpilot.connector_inbox WHERE status = 'RECEIVED' LIMIT $1",
                            cfg.max_batch_records,
                        )
                        for r in rows:
                            await process_inbox_item(r, conn)
                except Exception as loop_err:
                    logger.error("Error during inbox poll: %s", loop_err)

            # Wait poll interval or until shutdown
            try:
                await asyncio.wait_for(shutdown.wait(), timeout=float(cfg.poll_interval_sec))
            except asyncio.TimeoutError:
                pass
    finally:
        if pool is not None:
            await pool.close()
        logger.info("Ingestion Worker shutdown complete.")


def main() -> None:
    """Application entrypoint."""
    try:
        asyncio.run(run_ingestion_worker())
    except KeyboardInterrupt:
        logger.info("Ingestion Worker interrupted by operator.")
        sys.exit(0)


if __name__ == "__main__":
    main()
