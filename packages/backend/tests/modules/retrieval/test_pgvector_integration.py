"""
RevPilot AI — Unit Tests for pgvector HNSW Migration and Vector Repository Integration
Conforms to ADR-0006, docs/09-rag/RAG-SPEC.md, and INV-TEN-001.
"""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock
import pytest

from revpilot.modules.retrieval.adapters.postgres_evidence_repository import PostgresEvidenceRepository
from revpilot.shared.context import TenantContext
from revpilot.shared.identifiers import TenantId, OrganizationId
from revpilot.shared.temporal import UtcDateTime


class MockAsyncConn:
    def __init__(self):
        self.executed = []
        self.fetched = []
        self._tx = AsyncMock()

    async def execute(self, query: str, *args):
        self.executed.append((query, args))
        return "EXECUTE_OK"

    async def fetch(self, query: str, *args):
        self.fetched.append((query, args))
        return [
            {
                "id": "chk_001",
                "tenant_id": "tnt_alpha_01",
                "document_id": "doc_001",
                "chunk_index": 0,
                "content": "Sample revenue contract text.",
                "metadata": '{"source": "salesforce"}',
                "classification": "CONFIDENTIAL",
                "effective_from": UtcDateTime.now().as_datetime(),
                "effective_to": None,
                "distance": 0.05,
            }
        ]

    def transaction(self):
        return self._tx


class MockAsyncPool:
    def __init__(self, conn):
        self.conn = conn
        self.acquired = 0
        self.released = 0

    async def acquire(self):
        self.acquired += 1
        return self.conn

    async def release(self, conn):
        self.released += 1


def _load_migration_014():
    p = Path(__file__).resolve().parents[3] / "alembic" / "versions" / "014_pgvector_document_embeddings.py"
    spec = importlib.util.spec_from_file_location("migration_014", p)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_alembic_014_migration_metadata():
    """Verify Alembic 014 migration conforms to DAG lineage."""
    migration_014 = _load_migration_014()
    assert migration_014.revision == "014_pgvector_embeddings"
    assert migration_014.down_revision == "013_dq_lineage"
    assert callable(migration_014.upgrade)
    assert callable(migration_014.downgrade)


@pytest.mark.asyncio
async def test_save_document_chunk_executes_correct_sql():
    """Verify save_document_chunk formats vector and inserts with tenant context."""
    conn = MockAsyncConn()
    pool = MockAsyncPool(conn)

    repo = PostgresEvidenceRepository(pool=pool)
    context = TenantContext(tenant_id=TenantId("tnt_alpha_01"), organization_id=OrganizationId("org_01"))

    chunk_data = {
        "id": "chk_001",
        "document_id": "doc_001",
        "chunk_index": 0,
        "content": "Sample revenue contract text.",
        "metadata": {"source": "salesforce"},
        "classification": "CONFIDENTIAL",
        "embedding": [0.1, 0.2, 0.3],
    }

    result_id = await repo.save_document_chunk(context, chunk_data)
    assert result_id == "chk_001"

    # Verify executed queries
    assert len(conn.executed) >= 1
    # Check that insert query was called with proper parameters
    insert_queries = [e for e in conn.executed if "INSERT INTO revpilot.document_chunks" in e[0]]
    assert len(insert_queries) == 1
    query_args = insert_queries[0][1]
    assert query_args[0] == "tnt_alpha_01"
    assert query_args[1] == "chk_001"
    assert "[0.1,0.2,0.3]" in query_args[10]


@pytest.mark.asyncio
async def test_search_similar_chunks_cosine_query():
    """Verify search_similar_chunks executes cosine distance query against pgvector."""
    conn = MockAsyncConn()
    pool = MockAsyncPool(conn)

    repo = PostgresEvidenceRepository(pool=pool)
    context = TenantContext(tenant_id=TenantId("tnt_alpha_01"), organization_id=OrganizationId("org_01"))

    results = await repo.search_similar_chunks(context, [0.1, 0.2, 0.3], top_k=3)
    assert len(results) == 1
    assert results[0]["id"] == "chk_001"
    assert results[0]["similarity_score"] == pytest.approx(0.95, rel=1e-3)

    assert len(conn.fetched) == 1
    query_sql = conn.fetched[0][0]
    assert "<=> $1::vector" in query_sql
