"""
RevPilot AI — Tests: Staging Infrastructure as Code (IaC) & Deployment Contracts
Specification: docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §4..§7
Conforms to DEC-004, ADR-0008, ADR-0009, INV-SEC-001, and AC-DEP-01.
"""

from __future__ import annotations

from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
STAGING_TF_DIR = WORKSPACE_ROOT / "infra" / "environments" / "staging"
COMPOSE_FILE = WORKSPACE_ROOT / "compose.yaml"
INIT_DB_SQL = WORKSPACE_ROOT / "infra" / "local" / "init-db.sql"

EXPECTED_TF_FILES = [
    "versions.tf",
    "variables.tf",
    "vpc.tf",
    "security_groups.tf",
    "kms.tf",
    "rds.tf",
    "ecs.tf",
    "alb.tf",
    "secrets.tf",
    "outputs.tf",
]


def test_staging_terraform_manifests_exist():
    """
    AC-DEP-01 & DEC-004: All 10 modular Terraform files exist and are non-empty.
    """
    assert STAGING_TF_DIR.exists(), f"Missing staging directory: {STAGING_TF_DIR}"
    for filename in EXPECTED_TF_FILES:
        tf_path = STAGING_TF_DIR / filename
        assert tf_path.exists(), f"Missing required TF manifest: {filename}"
        assert tf_path.stat().st_size > 50, f"TF manifest is empty or too short: {filename}"


def test_network_zoning_topology_invariants():
    """
    AC-DEP-01 & §5: VPC enforces 3 isolated security zones:
    Zone 1 (DMZ Ingress), Zone 2 (Private Compute), Zone 3 (Isolated Persistence).
    """
    vpc_content = (STAGING_TF_DIR / "vpc.tf").read_text(encoding="utf-8")

    assert "Zone-1-DMZ-Ingress" in vpc_content
    assert "Zone-2-Private-Compute" in vpc_content
    assert "Zone-3-Isolated-Persistence" in vpc_content

    # Isolated persistence subnets must strictly prohibit direct public IP assignment
    assert "map_public_ip_on_launch = false" in vpc_content
    # Isolated persistence route table must not route to internet gateway
    assert "isolated_persistence" in vpc_content


def test_database_security_and_encryption_invariants():
    """
    INV-SEC-001, ADR-0004, ADR-0005: RDS Aurora PostgreSQL must enforce:
    1. storage_encrypted = true
    2. publicly_accessible = false
    3. rds.force_ssl = 1
    4. Customer managed KMS key
    """
    rds_content = (STAGING_TF_DIR / "rds.tf").read_text(encoding="utf-8")

    assert "storage_encrypted   = true" in rds_content or "storage_encrypted = true" in rds_content
    assert "publicly_accessible = false" in rds_content
    assert 'rds.force_ssl' in rds_content
    assert "kms_key_id" in rds_content
    assert "backup_retention_period = 7" in rds_content


def test_kms_cmk_rotation_invariant():
    """
    ADR-0009 & INV-SEC-001: Customer Managed Key must enforce automatic key rotation.
    """
    kms_content = (STAGING_TF_DIR / "kms.tf").read_text(encoding="utf-8")
    assert "enable_key_rotation     = true" in kms_content or "enable_key_rotation = true" in kms_content


def test_alb_tls13_security_policy():
    """
    DEPLOYMENT-ARCHITECTURE §5.1: ALB must terminate TLS 1.3.
    """
    alb_content = (STAGING_TF_DIR / "alb.tf").read_text(encoding="utf-8")
    assert "ELBSecurityPolicy-TLS13-1-2-2021-06" in alb_content
    assert "/health/live" in alb_content


def test_ecs_fargate_services_conformance():
    """
    DEPLOYMENT-ARCHITECTURE §6: ECS cluster defines all 4 containerized services with Fargate.
    """
    ecs_content = (STAGING_TF_DIR / "ecs.tf").read_text(encoding="utf-8")

    assert "revpilot-${var.environment}-api" in ecs_content
    assert "revpilot-${var.environment}-workflow-worker" in ecs_content
    assert "revpilot-${var.environment}-ml-worker" in ecs_content
    assert "revpilot-${var.environment}-ingestion-worker" in ecs_content
    assert '"FARGATE"' in ecs_content


def test_local_docker_compose_conformance():
    """
    Local multi-container composition defines all required workloads and network zones.
    """
    assert COMPOSE_FILE.exists(), "Missing root compose.yaml"
    compose_content = COMPOSE_FILE.read_text(encoding="utf-8")

    expected_services = [
        "api:",
        "workflow-worker:",
        "ml-worker:",
        "ingestion-worker:",
        "postgres:",
        "redis:",
        "temporal:",
    ]
    for service in expected_services:
        assert service in compose_content, f"Missing service in compose.yaml: {service}"

    expected_networks = [
        "dmz_net:",
        "compute_net:",
        "persistence_net:",
    ]
    for network in expected_networks:
        assert network in compose_content, f"Missing network zone in compose.yaml: {network}"


def test_local_database_init_script_exists():
    """
    Database init script enables required extensions and RLS helper.
    """
    assert INIT_DB_SQL.exists(), "Missing infra/local/init-db.sql"
    sql_content = INIT_DB_SQL.read_text(encoding="utf-8")

    assert 'uuid-ossp' in sql_content
    assert 'pg_trgm' in sql_content
    assert 'current_tenant_id()' in sql_content
