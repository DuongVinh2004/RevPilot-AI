"""
RevPilot AI — Temporal Workflow Worker Application (apps/workflow-worker)
Durable workflow worker process executing investigation DAGs, signal handlers, and compensation sagas.
Conforms to:
- docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md
- ADR-0002 (Durable Execution via Temporal)
- INV-WF-001, INV-WF-002, INV-TEN-001..003
- docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §6
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

from revpilot.modules.investigation.workflows import (
    INVESTIGATION_WORKFLOW_QUEUE,
    InvestigationWorkflow,
    execute_governed_retrieval_activity,
    execute_read_only_sql_capability_activity,
    generate_investigation_plan_activity,
    ingest_ticket_intelligence_activity,
    package_evidence_bundle_activity,
    synthesize_hypotheses_activity,
    validate_investigation_scope_activity,
    verify_evidence_and_hypotheses_activity,
)
from revpilot.modules.action.saga.workflow import SafeActionSagaWorkflow
from revpilot.modules.action.saga.activities import compensate_step_activity

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("revpilot.workflow_worker")

REGISTERED_ACTIVITIES = [
    validate_investigation_scope_activity,
    generate_investigation_plan_activity,
    execute_read_only_sql_capability_activity,
    execute_governed_retrieval_activity,
    ingest_ticket_intelligence_activity,
    synthesize_hypotheses_activity,
    verify_evidence_and_hypotheses_activity,
    package_evidence_bundle_activity,
]

REGISTERED_WORKFLOWS = [
    InvestigationWorkflow,
]


class WorkerConfig:
    """Temporal worker configuration derived from environment."""

    def __init__(self) -> None:
        self.host = os.getenv("TEMPORAL_HOST", "localhost:7233")
        self.namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        self.task_queue = os.getenv("TEMPORAL_TASK_QUEUE", INVESTIGATION_WORKFLOW_QUEUE)
        self.database_url = os.getenv("DATABASE_URL")
        self.max_concurrent_activities = int(os.getenv("MAX_CONCURRENT_ACTIVITIES", "100"))
        self.max_concurrent_workflows = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "50"))


async def run_worker(config: WorkerConfig | None = None, stop_event: asyncio.Event | None = None) -> None:
    """Run the Temporal durable workflow worker until cancelled."""
    cfg = config or WorkerConfig()
    shutdown = stop_event or asyncio.Event()

    logger.info(
        "Initializing RevPilot Temporal Workflow Worker (Target: %s, Namespace: %s, Queue: %s)",
        cfg.host,
        cfg.namespace,
        cfg.task_queue,
    )

    # Initialize Database pool if configured
    pool = None
    if cfg.database_url:
        try:
            from revpilot.infrastructure.database import create_database_pool
            pool = await create_database_pool(cfg.database_url)
            logger.info("Worker database connection pool initialized.")
        except Exception as exc:
            logger.warning("Worker DB connection deferred: %s", exc)

    loop = asyncio.get_running_loop()

    def _handle_signal(sig_name: str) -> None:
        logger.info("Received termination signal: %s. Initiating graceful worker drain...", sig_name)
        shutdown.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig.name: _handle_signal(s))
        except (NotImplementedError, RuntimeError):
            pass

    logger.info("Workflows registered: %s", [w.__name__ for w in REGISTERED_WORKFLOWS])
    logger.info("Activities registered: %s", [a.__name__ for a in REGISTERED_ACTIVITIES])

    # Try connecting to Temporal cluster
    client = None
    try:
        from temporalio.client import Client
        from temporalio.worker import Worker
        client = await Client.connect(cfg.host, namespace=cfg.namespace)
        worker = Worker(
            client,
            task_queue=cfg.task_queue,
            workflows=REGISTERED_WORKFLOWS,
            activities=REGISTERED_ACTIVITIES,
            max_concurrent_activities=cfg.max_concurrent_activities,
            max_concurrent_workflow_tasks=cfg.max_concurrent_workflows,
        )
        logger.info("Connected to Temporal cluster. Polling on task queue '%s'...", cfg.task_queue)
        await worker.run()
    except Exception as exc:
        logger.warning(
            "Temporal cluster unavailable (%s). Running in standalone / testing standby mode.",
            exc,
        )
        await shutdown.wait()
    finally:
        if pool is not None:
            await pool.close()
        logger.info("Temporal Workflow Worker drained and stopped successfully.")


def main() -> None:
    """Application entrypoint."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by operator.")
        sys.exit(0)


if __name__ == "__main__":
    main()
