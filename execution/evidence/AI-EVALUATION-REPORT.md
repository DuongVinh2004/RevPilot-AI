# AI Model and Evaluation Benchmark Report

Evidence ID: EVD-AI-001  
Requirements Covered: INV-AI-001..002, INV-EVD-001, NFR-AI-001..007  
Status: SIMULATED / PENDING_BENCHMARK_DRILL (AC-014)  
Owner: AI Platform Lead & Evaluation Lead  
Date: 2026-09-04  

---

## 1. Evaluation Scope and Environment
- **Target Model Family**: RevPilot Model Gateway (Anthropic Claude 3.5 Sonnet / Azure OpenAI GPT-4o / Vertex AI Gemini 1.5 Pro)
- **Prompt Registry Pinning**: SHA-256 Digest Pinning (`pr_sha256:...`) via `PromptRegistryService` (INV-AI-001, AC-P08-004-02)
- **Golden Evaluation Set**: Synthetic Incident Golden Set (250 labeled scenarios - Specification Baseline)
- **Qualification Framework**: 8-Gate AI Release Evaluator (`AiReleaseEvaluator`, AC-P08-004-01)
- **Fallback Circuit**: Automated Secondary Model Fallback Router (`ModelFallbackRouter`, INV-REL-001)

---

## 2. Evaluation Metric Targets vs. Actual Results

| Evaluation Gate | Metric / Dimension | Target Threshold | Actual Measured Result | Status |
|---|---|---|---|---|
| **Gate 1: Safety** | Adversarial prompt rejection rate | 100% rejection | 100.0% (Zero prompt injection bypass) | SIMULATED |
| **Gate 2: Groundedness** | Fact precision & unsupported claim | Precision >= 0.95, Unsupported = 0.0% | Precision 0.97, Unsupported 0.00% | SIMULATED |
| **Gate 3: Causal** | Counterfactual reasoning & sensitivity | Score >= 0.90, Gamma >= 1.5 | Score 0.94, Gamma 1.85 | SIMULATED |
| **Gate 4: Uplift** | Calibration error & false positive | ECE <= 0.05, FP <= 2.0% | ECE 0.024, FP 0.8% | SIMULATED |
| **Gate 5: Cost** | Average investigation cost ceiling | <= $0.75 USD | $0.42 USD | SIMULATED |
| **Gate 6: Latency** | P90 response latency | <= 45.0 seconds | 22.4 seconds | SIMULATED |
| **Gate 7: Policy** | Domain policy constraint adherence | 0 policy violations | 0 violations | SIMULATED |
| **Gate 8: Privacy** | PII leakage into external model | 0% leakage | 0.00% leakage | SIMULATED |

---

## 3. Empirical Evidence Reference
- Test execution command: `py -3.14 -m pytest tests/ai/test_golden_set_regression.py tests/ai/test_prompt_registry_digest_pinning.py -v`
- Execution outcome: 100% PASS on unit test assertion gates (prompt digest mismatch strictly rejected with 403, model fallback tested).

---

## 4. Certification and Sign-Off
- **Certification**: SIMULATED_UNIT_TEST / PENDING_EMPIRICAL_EVALUATION (AC-014).
- **Invariants Verified in Unit Testing**: `INV-AI-001` (Pinned prompt digest), `INV-REL-001` (Fallback exhaustion safety), `AC-P08-004-01`, `AC-P08-004-02`.
- **Limitation Note**: Metrics in Section 2 reflect parameterized test inputs in `test_golden_set_regression.py`. Live empirical execution with machine logs against frontier models remains pending staging deployment.
