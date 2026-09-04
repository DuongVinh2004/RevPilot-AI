"""
RevPilot AI — Reciprocal Rank Fusion (RRF) Algorithm
Specification: docs/09-rag/RAG-SPEC.md §2.1 (Step 7), §5
Combines sparse lexical (BM25) and dense vector (HNSW) retrieval rankings.
"""

from __future__ import annotations


def reciprocal_rank_fusion(
    lexical_ranks: dict[str, int],
    dense_ranks: dict[str, int],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Combine rankings using standard Reciprocal Rank Fusion formula:
        RRF_Score(d) = sum_{m in {lexical, dense}} 1 / (k + rank_m(d))
    
    Ranks must be 1-based integers (1 is top ranked item).
    Returns list of (chunk_id, rrf_score) tuples sorted descending by score.
    """
    if k <= 0:
        raise ValueError(f"RRF smoothing constant k must be positive, got {k}")

    all_chunk_ids = set(lexical_ranks.keys()) | set(dense_ranks.keys())
    scores: dict[str, float] = {}

    for chunk_id in all_chunk_ids:
        score = 0.0
        if chunk_id in lexical_ranks:
            rank = lexical_ranks[chunk_id]
            if rank < 1:
                raise ValueError(f"Ranks must be 1-indexed positive integers, got {rank} for {chunk_id}")
            score += 1.0 / (k + rank)

        if chunk_id in dense_ranks:
            rank = dense_ranks[chunk_id]
            if rank < 1:
                raise ValueError(f"Ranks must be 1-indexed positive integers, got {rank} for {chunk_id}")
            score += 1.0 / (k + rank)

        scores[chunk_id] = score

    # Deterministic sort: descending by score, ascending by chunk_id for tie-breaking
    sorted_items = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    return sorted_items
