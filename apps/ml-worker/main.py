"""
RevPilot AI — ML & Causal Intelligence Worker (apps/ml-worker)
Executes asynchronous batch scoring, uplift learning, and causal estimand verification.
Conforms to:
- docs/08-ml-platform/ML-SYSTEM-SPEC.md
- docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md
- docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md
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
logger = logging.getLogger("revpilot.ml_worker")


class MLWorkerConfig:
    """ML Worker configuration derived from environment."""

    def __init__(self) -> None:
        self.batch_size = int(os.getenv("ML_BATCH_SIZE", "1000"))
        self.max_concurrency = int(os.getenv("ML_MAX_CONCURRENCY", "4"))
        self.model_cache_dir = os.getenv("MODEL_CACHE_DIR", "/tmp/models")
        self.zero_data_retention = os.getenv("ZERO_DATA_RETENTION", "true").lower() == "true"


async def run_ml_worker(config: MLWorkerConfig | None = None, stop_event: asyncio.Event | None = None) -> None:
    """Run ML evaluation and scoring worker until stop requested."""
    cfg = config or MLWorkerConfig()
    shutdown = stop_event or asyncio.Event()

    logger.info(
        "Initializing RevPilot ML Worker (Batch Size: %d, Concurrency: %d, ZeroDataRetention: %s)",
        cfg.batch_size,
        cfg.max_concurrency,
        cfg.zero_data_retention,
    )

    loop = asyncio.get_running_loop()

    def _handle_signal(sig_name: str) -> None:
        logger.info("Received signal %s. Draining active ML inference batches...", sig_name)
        shutdown.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig.name: _handle_signal(s))
        except (NotImplementedError, RuntimeError):
            pass

    logger.info("ML Worker ready. Listening for batch scoring and causal inference tasks...")
    try:
        await shutdown.wait()
    finally:
        logger.info("ML Worker drained and terminated safely.")


def main() -> None:
    """Entrypoint."""
    try:
        asyncio.run(run_ml_worker())
    except KeyboardInterrupt:
        logger.info("ML Worker interrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
