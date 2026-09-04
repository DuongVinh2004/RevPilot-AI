# Continuous Evaluation Report Template

Template ID: TMPL-EVAL-001  
Owner: AI Evaluation Lead & AI Platform Lead  
Status: OPERATIONAL TEMPLATE (Not an executed evaluation report)  
Reference: EVALUATION-FRAMEWORK.md, MODEL-RELEASE-PROCESS.md  

---

## 1. Evaluation Run Metadata
- **Evaluation Run ID**: EVAL-[YYYYMMDD]-[RUN_ID]
- **Date of Execution**: YYYY-MM-DD
- **Evaluator**: [Name / Automated CI Pipeline]
- **Model Identifier & Snapshot**: [e.g., claude-3-5-sonnet-20241022 / gpt-4o-2024-08-06]
- **Prompt Template Version & Digest**: prompts/investigation/root_cause_v[X.Y].json (SHA256:[HASH])
- **Vector Index Version**: idx_v[X.Y] (Embedding Model: [Embedding Model Name])
- **Policy Engine Configuration**: policy_rules_v[X.Y]

---

## 2. Benchmark Dataset & Slice Information
- **Dataset Version**: eval_golden_v[X.Y]
- **Total Test Cases**: [e.g., 250 labeled scenarios]
- **Tenant Slices Evaluated**: [SMB profile, Enterprise profile, High-Volume Logistics slice]

---

## 3. Evaluation Results vs. Gating Thresholds

| Evaluation Metric | Gate Threshold | Prior Baseline | Current Measured | Delta | Gate Verdict |
|---|---|---|---|---|---|
| **Root Cause Localization (Top-1)** | >= 0.80 | [Score] | [Score] | [+/- Delta] | [PASS / FAIL] |
| **Root Cause Localization (Top-3)** | >= 0.95 | [Score] | [Score] | [+/- Delta] | [PASS / FAIL] |
| **Groundedness Score** | >= 0.95 | [Score] | [Score] | [+/- Delta] | [PASS / FAIL] |
| **Citation Precision** | >= 0.95 | [Score] | [Score] | [+/- Delta] | [PASS / FAIL] |
| **Unsupported Claim Acceptance Rate** | = 0.00% | [Rate] | [Rate] | [+/- Delta] | [PASS / FAIL] |
| **Adversarial Safety / Injection**| 100% block | [Rate] | [Rate] | [+/- Delta] | [PASS / FAIL] |
| **P95 Gateway Latency** | <= 2,500ms | [ms] | [ms] | [+/- ms] | [PASS / FAIL] |
| **Cost per Investigation** | <= USD 2.00 target; USD 5.00 hard stop | [$] | [$] | [+/- $] | [PASS / FAIL] |
| **Concept Drift Detection (KS-test)**| p-value > 0.05 | [p-val] | [p-val] | [Status] | [PASS / FAIL] |

---

## 4. Qualitative Analysis & Failure Modes
- **False Negative Analysis**: [Summary of anomalies missed by detector/verifier]
- **Hallucination / Unsupported Claims**: [Specific cited IDs that failed provenance check]
- **Safety / Guardrail Blocks**: [Any safe queries blocked falsely or malicious inputs slipped through]

---

## 5. Promotion Recommendation
- **Recommendation Verdict**: [PROMOTE TO PRODUCTION / REJECT / CANARY ONLY]
- **Approver Sign-off**: [AI Governance Lead / Date]
