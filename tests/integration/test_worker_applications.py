"""
RevPilot AI — Tests: Worker Application Entrypoints (apps/*-worker)
Specification: docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §6
Conforms to INV-WF-001, INV-AI-001, and AC-DEP-01.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT / "packages" / "backend" / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import importlib
import pytest


def test_workflow_worker_configuration_and_registration():
    """
    AC-DEP-01 & INV-WF-001: Workflow worker loads configuration and registers
    InvestigationWorkflow and canonical activities.
    """
    mod = importlib.import_module("apps.workflow-worker.main")
    config = mod.WorkerConfig()

    assert config.host == "localhost:7233" or ":" in config.host
    assert config.namespace == "default"
    assert config.task_queue == "investigation-workflow-queue"

    # Verify workflow registration
    workflow_names = [w.__name__ for w in mod.REGISTERED_WORKFLOWS]
    assert "InvestigationWorkflow" in workflow_names

    # Verify activity registration (8 canonical activities)
    activity_names = [a.__name__ for a in mod.REGISTERED_ACTIVITIES]
    assert len(activity_names) == 8
    assert "validate_investigation_scope_activity" in activity_names
    assert "generate_investigation_plan_activity" in activity_names
    assert "execute_read_only_sql_capability_activity" in activity_names
    assert "execute_governed_retrieval_activity" in activity_names
    assert "ingest_ticket_intelligence_activity" in activity_names
    assert "synthesize_hypotheses_activity" in activity_names
    assert "verify_evidence_and_hypotheses_activity" in activity_names
    assert "package_evidence_bundle_activity" in activity_names


def test_ml_worker_configuration():
    """
    AC-DEP-01 & INV-AI-001: ML worker loads configuration and enforces zero data retention default.
    """
    mod = importlib.import_module("apps.ml-worker.main")
    config = mod.MLWorkerConfig()

    assert config.batch_size > 0
    assert config.max_concurrency > 0
    assert config.zero_data_retention is True


def test_ingestion_worker_configuration():
    """
    AC-DEP-01 & DEC-006: Ingestion worker loads configuration with poll interval and batch limits.
    """
    mod = importlib.import_module("apps.ingestion-worker.main")
    config = mod.IngestionConfig()

    assert config.poll_interval_sec >= 10
    assert config.max_batch_records >= 100
    assert "redis://" in config.redis_url
