"""014_pgvector_document_embeddings

Revision ID: 014_pgvector_embeddings
Revises: 013_dq_lineage
Create Date: 2026-09-05 12:00:00.000000

Conforms to:
- docs/09-rag/RAG-SPEC.md §2, §3
- docs/31-adr/ADR-0006-retrieval-baseline.md
- docs/27-database/DATABASE-SCHEMA.md
- INV-EVD-001, INV-TEN-001, INV-SEC-002
"""

from typing import Sequence, Union
from alembic import op

revision: str = "014_pgvector_embeddings"
down_revision: Union[str, None] = "013_dq_lineage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Graceful vector extension creation
    op.execute("""
    DO $$
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector;
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'pgvector extension not installed or unavailable; continuing with fallback';
    END
    $$;
    """)

    # 2. Document Chunks Table with Tenant RLS
    op.execute("""
    CREATE TABLE IF NOT EXISTS revpilot.document_chunks (
        tenant_id VARCHAR(64) NOT NULL,
        id VARCHAR(64) NOT NULL,
        document_id VARCHAR(64) NOT NULL,
        chunk_index INT NOT NULL DEFAULT 0,
        content TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        classification VARCHAR(32) NOT NULL DEFAULT 'INTERNAL',
        effective_from TIMESTAMPTZ NOT NULL,
        effective_to TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_document_chunks PRIMARY KEY (tenant_id, id),
        CONSTRAINT fk_document_chunks_tenant FOREIGN KEY (tenant_id)
            REFERENCES revpilot.tenants (id) ON DELETE RESTRICT
    );
    """)

    # 3. Add embedding column and HNSW index if pgvector is available, else float8[] fallback
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
            ALTER TABLE revpilot.document_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536);
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
                ON revpilot.document_chunks USING hnsw (embedding vector_cosine_ops);
        ELSE
            ALTER TABLE revpilot.document_chunks ADD COLUMN IF NOT EXISTS embedding float8[];
        END IF;
    END
    $$;
    """)

    # 4. Standard query indices
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_document_chunks_doc ON revpilot.document_chunks (tenant_id, document_id);
    CREATE INDEX IF NOT EXISTS idx_document_chunks_effective ON revpilot.document_chunks (tenant_id, effective_from, effective_to);
    """)

    # 5. RLS Policy Enforcement (INV-TEN-001)
    op.execute("""
    ALTER TABLE revpilot.document_chunks ENABLE ROW LEVEL SECURITY;
    ALTER TABLE revpilot.document_chunks FORCE ROW LEVEL SECURITY;
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE schemaname = 'revpilot' AND tablename = 'document_chunks' AND policyname = 'tenant_isolation'
        ) THEN
            CREATE POLICY tenant_isolation ON revpilot.document_chunks AS RESTRICTIVE
                USING (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true))
                WITH CHECK (current_setting('revpilot.is_system', true) = 'true' OR tenant_id = current_setting('revpilot.current_tenant_id', true));
        END IF;
    END
    $$;
    """)

    # 6. Role grants
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'revpilot_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON revpilot.document_chunks TO revpilot_app;
        END IF;
        IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'revpilot_readonly') THEN
            GRANT SELECT ON revpilot.document_chunks TO revpilot_readonly;
        END IF;
    END
    $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revpilot.document_chunks CASCADE;")
