"""005_analytics_anomaly_tables

Revision ID: 005_analytics
Revises: 004_canonical_data
Create Date: 2026-09-05 11:00:00.000000

Conforms to:
- docs/02-domain/ANOMALY-DOMAIN-SPEC.md
- docs/02-domain/ANOMALY-LOCALIZATION-SPEC.md
- docs/27-database/DATABASE-SCHEMA.md §10
- INV-AI-001, INV-TEN-001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005_analytics'
down_revision: Union[str, None] = '004_canonical_data'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Anomaly Records
    op.execute("""
    CREATE TABLE revpilot.anomaly_records (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        anomaly_type VARCHAR(32) NOT NULL,
        metric_id VARCHAR(64) NOT NULL,
        metric_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
        detector_id VARCHAR(64) NOT NULL,
        detector_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
        baseline_id VARCHAR(64),
        baseline_version VARCHAR(16),
        observation_window_start TIMESTAMPTZ NOT NULL,
        observation_window_end TIMESTAMPTZ NOT NULL,
        comparison_window_start TIMESTAMPTZ,
        comparison_window_end TIMESTAMPTZ,
        event_time TIMESTAMPTZ NOT NULL,
        effective_from TIMESTAMPTZ NOT NULL,
        effective_to TIMESTAMPTZ,
        as_of_time TIMESTAMPTZ NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actual_value NUMERIC(18,4) NOT NULL,
        expected_value NUMERIC(18,4) NOT NULL,
        expected_interval_lower NUMERIC(18,4),
        expected_interval_upper NUMERIC(18,4),
        anomaly_score NUMERIC(6,4) NOT NULL,
        severity VARCHAR(16) NOT NULL,
        affected_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
        data_freshness VARCHAR(32) NOT NULL DEFAULT 'FRESH',
        data_quality_state VARCHAR(32) NOT NULL DEFAULT 'PASSED',
        confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0000,
        supporting_evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
        status VARCHAR(32) NOT NULL DEFAULT 'DETECTED',
        reproducibility_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_anomaly_records PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_anomaly_records_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT ck_anomaly_score CHECK (anomaly_score >= 0.0000 AND anomaly_score <= 1.0000),
        CONSTRAINT ck_anomaly_severity CHECK (severity IN ('CRITICAL', 'MAJOR', 'MINOR', 'INFORMATIONAL')),
        CONSTRAINT ck_anomaly_status CHECK (status IN ('DETECTED', 'VALIDATED', 'LOCALIZED', 'ACKNOWLEDGED', 'SUPPRESSED', 'RESOLVED', 'REOPENED'))
    );
    CREATE INDEX idx_anomaly_records_tenant_status ON revpilot.anomaly_records (tenant_id, status, created_at DESC);
    CREATE INDEX idx_anomaly_records_tenant_metric ON revpilot.anomaly_records (tenant_id, metric_id, observation_window_start);

    ALTER TABLE revpilot.anomaly_records ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.anomaly_records FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.anomaly_records AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 2. Anomaly Localizations
    op.execute("""
    CREATE TABLE revpilot.anomaly_localizations (
        tenant_id VARCHAR(64) NOT NULL,
        localization_id VARCHAR(64) NOT NULL,
        anomaly_id VARCHAR(64) NOT NULL,
        metric_id VARCHAR(64) NOT NULL,
        evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        as_of_time TIMESTAMPTZ NOT NULL,
        dimension_evaluated VARCHAR(64) NOT NULL,
        data_coverage_pct NUMERIC(5,2) NOT NULL,
        top_contributing_segments JSONB NOT NULL DEFAULT '[]'::jsonb,
        suppressed_segments_count INT NOT NULL DEFAULT 0,
        association_summary TEXT NOT NULL,
        diagnostic_status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
        lineage_trace_id VARCHAR(64) NOT NULL,
        CONSTRAINT pk_anomaly_localizations PRIMARY KEY (tenant_id, localization_id),
        CONSTRAINT fk_anomaly_localizations_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT,
        CONSTRAINT fk_anomaly_localizations_anomaly FOREIGN KEY (tenant_id, anomaly_id)
            REFERENCES revpilot.anomaly_records (tenant_id, id) ON DELETE CASCADE
    );
    CREATE INDEX idx_anomaly_loc_anomaly ON revpilot.anomaly_localizations (tenant_id, anomaly_id);

    ALTER TABLE revpilot.anomaly_localizations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.anomaly_localizations FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.anomaly_localizations AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 3. Metric Baselines
    op.execute("""
    CREATE TABLE revpilot.metric_baselines (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        metric_id VARCHAR(64) NOT NULL,
        baseline_type VARCHAR(32) NOT NULL,
        parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
        version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
        is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_metric_baselines PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_metric_baselines_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT
    );
    CREATE INDEX idx_metric_baselines_metric ON revpilot.metric_baselines (tenant_id, metric_id, version);

    ALTER TABLE revpilot.metric_baselines ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.metric_baselines FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.metric_baselines AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)

    # 4. Detector Runs
    op.execute("""
    CREATE TABLE revpilot.detector_runs (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        anomaly_id VARCHAR(64),
        detector_id VARCHAR(64) NOT NULL,
        input_hash VARCHAR(64) NOT NULL,
        output_hash VARCHAR(64) NOT NULL,
        duration_ms INT NOT NULL,
        executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_detector_runs PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_detector_runs_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT
    );
    CREATE INDEX idx_detector_runs_detector ON revpilot.detector_runs (tenant_id, detector_id, executed_at DESC);

    ALTER TABLE revpilot.detector_runs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.detector_runs FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON revpilot.detector_runs AS RESTRICTIVE
        USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
        WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.detector_runs CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.metric_baselines CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.anomaly_localizations CASCADE;")
    op.execute("DROP TABLE IF EXISTS revpilot.anomaly_records CASCADE;")
