# TASK-DA-010 — Map AI Governance Controls to NIST AI RMF 1.0 and OWASP Top 10 for LLM

1. **Task ID**: TASK-DA-010
2. **Parent Finding ID**: FINDING-010
3. **Title**: Map AI Governance Controls to NIST AI RMF 1.0 and OWASP Top 10 for LLM
4. **Objective**: Add an Appendix to docs/19-ai-governance/AI-GOVERNANCE.md mapping platform AI invariants to NIST AI RMF functions and OWASP LLM Top 10 risks.
5. **Single Expected Outcome**: docs/19-ai-governance/AI-GOVERNANCE.md contains complete standards alignment tables.
6. **Scope**: Appendix of docs/19-ai-governance/AI-GOVERNANCE.md.
7. **Non-Goals**: Modifying model release gates; rewriting prompt schemas.
8. **Exact File(s)**: `docs/19-ai-governance/AI-GOVERNANCE.md`
9. **Exact Section(s)**: §Appendix: Industry Standards Alignment (NIST AI RMF & OWASP LLM)
10. **Input**: NIST AI 100-1 specification; OWASP Top 10 for LLM Applications (2025).
11. **Output**: Updated docs/19-ai-governance/AI-GOVERNANCE.md with mapping tables.
12. **Preconditions**: FINDING-010 open.
13. **Invariant / Requirement Affected**: `INV-AI-001..002, INV-SEC-002, INV-ACT-001..004`
14. **Detailed Atomic Steps**:
1. Structure mapping table for NIST AI RMF 1.0 functions: GOVERN, MAP, MEASURE, MANAGE.
2. Map RevPilot AI controls (evaluation golden set, prompt registry, citation verifier, human approval gate) to NIST subcategories.
3. Structure mapping table for OWASP Top 10 for LLM: LLM01 (Prompt Injection), LLM02 (Sensitive Info Disclosure), LLM06 (Excessive Agency).
4. Append mapping section to docs/19-ai-governance/AI-GOVERNANCE.md.

15. **Acceptance Criteria**:
    - `AC-DA-010-01: AI-GOVERNANCE.md contains explicit cross-reference tables for NIST AI RMF 1.0 and OWASP Top 10 for LLM Applications.`
16. **Validation Method**:
    ```powershell
    python -c "t = open('docs/19-ai-governance/AI-GOVERNANCE.md', encoding='utf-8').read(); assert 'NIST AI RMF' in t; assert 'OWASP' in t"
    ```
17. **Evidence Artifact**: `docs/19-ai-governance/AI-GOVERNANCE.md diff`
18. **Owner Role**: AI Governance Lead & Security Reviewer
19. **Estimated Size**: 60 min
20. **Dependencies**: `None`
21. **Blocks**: `None`
22. **Risk**: Excessive text length without added governance rigor.
23. **Recovery Note**: Keep mappings in structured table format with direct invariant cross-references.
24. **Status**: SUPERSEDED (Resolved by FINAL-DOCUMENTATION-REMEDIATION)
25. **Traceability**: `FINDING-010 -> TASK-DA-010 -> docs/19-ai-governance/AI-GOVERNANCE.md`
