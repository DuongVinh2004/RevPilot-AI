# Governed Retrieval and RAG Contract

Status: Proposed v0.1 — E02 specification output

## Entities and ownership

Retrieval owns rebuildable `Document`, `DocumentVersion`, `ChunkProjection`, and `IndexManifest`; Evidence owns the immutable cited Evidence record. A document version has source URI/reference, tenant, ACL, classification, source/effective/as-of times, supersession state, parser/chunking/embedding versions and digest. PostgreSQL FTS plus pgvector is the baseline; Qdrant/OpenSearch require ADR-0006 triggers.

## Retrieval pipeline

The `RetrievalPort` requires trusted tenant and authorization context, query, filters, as-of/effective time, index version, limit and deadline. It applies tenant/ACL/effective-date/supersession filters in retrieval and revalidates candidates before context construction. Lexical and dense candidates are independently retrieved, deterministically fused, optionally reranked, then converted to bounded cited Evidence references. Context contains only authorized minimized excerpts and citation metadata. No result means `NO_AUTHORIZED_EVIDENCE`, not a model invitation to invent content.

## Lifecycle and gates

Ingest/version, index, reindex, supersede, revoke and delete are explicit projection transitions. Deletion or ACL change makes a chunk unavailable immediately to new queries and queues rebuild/reconciliation; failed parsing quarantines the version with safe diagnostics. Required evaluation includes Recall@10, MRR, citation precision, tenant/ACL/effective-date/supersession negatives, prompt-injection corpus, index lag, and rebuild hash reconciliation.

## Traceability

`INV-EVD-001..002`, `INV-TEN-001..002`, `INV-SEC-002`, `NFR-AI-003`; ADR-0004..0006.
