# Unsupported Claim Policy and Deterministic Verifier Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 04 — Hypothesis, Causal Analysis, and Verification (Rails 11, 12)
Owner: AI Platform Architecture / Formal Verification
Traceability: `INV-AI-001`, `INV-AI-002`, `INV-SEC-002`, `INV-DATA-001`, `INV-EVD-001..002`, `INV-TEN-001..003`, `FR-RCA-002`, `AC-004`, `AC-013`, `ADR-0003`

---

## 1. Principles of Claim Verification

In RevPilot AI, natural language claims synthesized by LLM agents are treated as **untrusted cognitive proposals** until formally validated by a deterministic verifier. Unsubstantiated model statements, ungrounded causal assertions, and uncalibrated probabilities are strictly barred from release (`INV-AI-001`).

### 1.1 Non-Negotiable Invariants
1. **Zero Hallucinated Factuality (`INV-AI-001`)**: Every assertion of business fact, metric deviation, or root cause must point to verified evidence in an immutable `EvidenceBundle`.
2. **Strict Epistemic Claim Boundaries**: Claims must be labeled with their precise epistemic category. Conflating an association with a causal mechanism or presenting an unverified correlation as a treatment effect is an immediate rejection trigger.
3. **Deterministic Verification**: The verifier operates via deterministic code, string-offset matching, and mathematical validation—not by prompting another LLM to "grade" text.
4. **Mandatory Fallback to `NEED_MORE_EVIDENCE` (`FR-RCA-002`)**: When claims lack sufficient backing evidence or encounter unresolvable contradictions, the verifier assigns status `NEED_MORE_EVIDENCE` or `UNSUPPORTED`.
5. **No Model Authority Creation (`INV-SEC-002`, `SEC-004`)**: Verifier outcomes cannot grant permissions, escalate privileges, or authorize external actions.

---

## 2. Claim Taxonomy and Data Contract

### 2.1 Claim Classification
Every atomic proposition within a hypothesis, report, or analysis is categorized into one of 6 formal claim types:

| Claim Category | Definition | Required Evidence Standard | Rejection Trigger |
|---|---|---|---|
| **DIRECTLY_OBSERVED** | Raw event or record explicitly stored in canonical database | Verified row hash or immutable document chunk offset | Missing record, record timestamped after `:as_of_time` |
| **DERIVED_STATISTIC** | Deterministic mathematical calculation over canonical data | Registered metric ID, formula, input dataset version, reproducible query digest | Formula discrepancy, zero-division error, uncatalogued query |
| **ASSOCIATION** | Observed statistical correlation or joint distribution co-occurrence | Pearson/Spearman $r$, mutual information, p-value, sample size $N \ge 30$ | Inferring causal direction, claiming intervention effect |
| **CAUSAL_ESTIMATE** | Point estimate and uncertainty interval from formal identification | Registered `CausalStudy`, identified estimand (ATE/ATT/CATE), overlap test, sensitivity bound | Correlation without identification, missing confounders, no interval |
| **UNSUPPORTED_INFERENCE**| Speculative narrative, plausibility guess, or ungrounded statement | None (Unacceptable in release artifacts) | Automatic rejection (`UNSUPPORTED`) |
| **POLICY_ACTION_CLAIM** | Assertion regarding policy eligibility, approval tier, or intervention | Policy engine evaluation digest, rule ID | Agent asserting policy authority without policy engine run |

### 2.2 Canonical Claim Schema
```python
class ClaimCategory(str, Enum):
    DIRECTLY_OBSERVED = "DIRECTLY_OBSERVED"
    DERIVED_STATISTIC = "DERIVED_STATISTIC"
    ASSOCIATION = "ASSOCIATION"
    CAUSAL_ESTIMATE = "CAUSAL_ESTIMATE"
    UNSUPPORTED_INFERENCE = "UNSUPPORTED_INFERENCE"
    POLICY_ACTION_CLAIM = "POLICY_ACTION_CLAIM"

class ClaimVerifierStatus(str, Enum):
    VERIFIED = "VERIFIED"                       # Validated against authoritative evidence
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED" # Plausible, non-authoritative evidence
    UNSUPPORTED = "UNSUPPORTED"                 # Zero evidence or citation mismatch
    CONTRADICTED = "CONTRADICTED"               # Authoritative evidence disproves claim
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"   # Data missing or incomplete sample
    UNAVAILABLE = "UNAVAILABLE"                 # Source system or index offline

class VerifiedClaim(BaseModel):
    claim_id: str                              # E.g. "clm_01h8abcde123"
    hypothesis_id: str
    statement: str
    category: ClaimCategory
    evidence_references: List[UUIDv7]          # Referenced EvidenceRecord IDs
    metric_id: Optional[str] = None
    data_snapshot_digest: Optional[str] = None
    temporal_as_of: UtcDateTime
    calculation_method: Optional[str] = None
    stated_assumptions: List[str] = Field(default_factory=list)
    stated_limitations: List[str] = Field(default_factory=list)
    confidence_interval: Optional[Tuple[float, float]] = None
    verifier_status: ClaimVerifierStatus
    rejection_reason: Optional[str] = None
    verified_at: UtcDateTime
```

---

## 3. Strict Rejection Triggers

The deterministic verifier immediately rejects a claim (`verifier_status = UNSUPPORTED` or `CONTRADICTED`) upon encountering any of the following 11 conditions:

1. **Missing Evidence**: The claim cites zero `evidence_references`.
2. **Unprovenanced Evidence**: The cited evidence lacks an authoritative source URI or content digest (`INV-EVD-001`).
3. **Expired or Superseded Evidence**: The cited contract clause or SLA was superseded or expired at `:as_of_time` (`INV-EVD-002`, `FR-EVD-003`).
4. **Tenant or ACL Mismatch**: The evidence belongs to a different tenant or an unauthorized ACL tier (`INV-TEN-001`).
5. **Estimand Overreach**: The claim asserts a causal relationship (e.g. "X caused Y") but cites only an association or correlation without an identified `CausalStudy`.
6. **Correlation Conflation**: Treating observed co-movement ($r > 0$) as an intervention effect or proof of root cause.
7. **Churn Risk Conflation**: Treating high baseline churn risk as equivalent to treatment uplift or intervention effectiveness.
8. **Violation of Identification Assumptions**: Causal claim lacks positivity/overlap checks, ignores key confounders, or conditioning on colliders/post-treatment variables.
9. **Temporal Lookahead / Data Leakage**: Claim relies on events or data timestamped after the evaluation `:as_of_time` (`INV-DATA-001`).
10. **Model Self-Authorization**: The text purports to authorize actions, waive penalties, or override policy without a server-side engine check (`INV-SEC-002`).
11. **Uncalibrated Confidence**: Representing model generation probability as statistical confidence (e.g. "I am 95% confident") without calibrated basis.

---

## 4. Verification Engine Architecture

```text
       [Candidate Hypothesis & Claims]
                      │
                      ▼
        [Claim Category Classifier]
                      │
                      ▼
     ┌────────────────────────────────┐
     │ Deterministic Validation Gates │
     ├────────────────────────────────┤
     │ 1. Citation Span Match Check   │
     │ 2. Tenant / ACL Cross-Check    │
     │ 3. As-Of Temporal Filter Check │
     │ 4. Metric Formula Audit        │
     │ 5. Contradiction Detection     │
     └────────────────┬───────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
[All Gates PASS]           [Any Gate FAILS]
        │                           │
        ▼                           ▼
  status: VERIFIED           Rejection Classifier
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
               UNSUPPORTED    CONTRADICTED   NEED_MORE_EVIDENCE
```

### Contradiction Detection Rules
The verifier evaluates negative probes against candidate claims:
- For claim: "Facility Midwest experienced no outbound issues"
- Check evidence: `canonical_shipments` where `origin_warehouse = 'WH-MIDWEST-01'` and `delayed_status = TRUE`.
- If delayed shipment count > 30, claim is marked `CONTRADICTED`, and parent hypothesis is penalized.

---

## 5. Automated Verification Test Suite Mapping

- `tests/ai-evals/test_unsupported_claim_rejection.py`: Tests that 100% of claims lacking evidence citations receive status `UNSUPPORTED` (`INV-AI-001`).
- `tests/ai-evals/test_correlation_causation_rejection.py`: Injects correlation-only claims stating "caused"; verifies verifier rejects with `ERR_CORRELATION_AS_CAUSATION`.
- `tests/ai-evals/test_claim_temporal_leakage.py`: Injects future-dated facts into claims; verifies verifier rejects with `ERR_TEMPORAL_LEAKAGE`.
- `tests/ai-evals/test_claim_contradiction_detection.py`: Injects false statements contrary to canonical database; verifies status `CONTRADICTED`.
