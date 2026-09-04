"""
RevPilot AI — Tests: Prompt Registry Cryptographic Digest Pinning
Specification: docs/20-evaluation/MODEL-RELEASE-PROCESS.md §4.2
Conforms to INV-AI-001, TC-P08-022, AC-011, AC-P08-004-02.
"""

from __future__ import annotations

import pytest

from revpilot.modules.ai_governance.release import (
    PromptDefinition,
    PromptDigestMismatchError,
    PromptRegistryService,
)


@pytest.fixture
def registry() -> PromptRegistryService:
    return PromptRegistryService()


def test_prompt_registration_and_digest_pinning(registry: PromptRegistryService):
    """
    AC-P08-004-02: Registering a prompt produces an immutable pr_sha256:... digest.
    """
    raw_prompt = (
        "You are RevPilot Investigation Agent. "
        "Analyze revenue anomalies using strictly cited ground-truth data."
    )
    defn: PromptDefinition = registry.register_prompt(
        template_name="investigation_agent_core",
        raw_template=raw_prompt,
        version="v1.0",
        author_principal="principal:ai-governance-lead",
    )

    assert defn.template_name == "investigation_agent_core"
    assert defn.sha256_digest.startswith("pr_sha256:")
    assert len(defn.sha256_digest) == len("pr_sha256:") + 64
    assert defn.version == "v1.0"
    assert defn.status == "ACTIVE"

    # Execution with identical prompt text succeeds
    validated = registry.validate_prompt_execution("investigation_agent_core", raw_prompt)
    assert validated.sha256_digest == defn.sha256_digest


def test_tampered_prompt_rejected_with_403(registry: PromptRegistryService):
    """
    AC-P08-004-02 & INV-AI-001:
    Altering even a single character in the prompt string fails validation with 403 Forbidden.
    """
    original = "You are RevPilot Investigation Agent. Never execute unapproved mutations."
    registry.register_prompt(
        template_name="action_agent_core",
        raw_template=original,
        version="v1.0",
    )

    # 1-character modification: mutation -> mutation. (added period or changed phrasing)
    tampered = "You are RevPilot Investigation Agent. Never execute unapproved mutations!"

    with pytest.raises(PromptDigestMismatchError) as exc_info:
        registry.validate_prompt_execution("action_agent_core", tampered)

    assert exc_info.value.code == "PROMPT_DIGEST_MISMATCH"
    assert exc_info.value.status_code == 403
    assert exc_info.value.details["template_name"] == "action_agent_core"
    assert "expected_digest" in exc_info.value.details
    assert "computed_digest" in exc_info.value.details

    # Verify audit event emitted
    tamper_events = [e for e in registry.audit_events if e["event_type"] == "PROMPT_TAMPER_DETECTED"]
    assert len(tamper_events) == 1
    assert tamper_events[0]["details"]["template_name"] == "action_agent_core"


def test_unregistered_prompt_rejected_with_403(registry: PromptRegistryService):
    """
    Executing an unpinned prompt name raises PromptDigestMismatchError (403).
    """
    with pytest.raises(PromptDigestMismatchError) as exc_info:
        registry.validate_prompt_execution("unregistered_random_template", "Any prompt content")

    assert exc_info.value.code == "PROMPT_DIGEST_MISMATCH"
    assert exc_info.value.status_code == 403


def test_prompt_version_reversion_and_rollback(registry: PromptRegistryService):
    """
    Prompt template can be rolled back cleanly to a historical version (§6.2).
    """
    v1_text = "Prompt template version 1"
    v2_text = "Prompt template version 2 with updated instructions"

    registry.register_prompt("anomaly_prompt", v1_text, version="v1.0")
    v2_defn = registry.register_prompt("anomaly_prompt", v2_text, version="v2.0")

    # Currently active is v2
    assert registry.get_active_prompt("anomaly_prompt").version == "v2.0"
    registry.validate_prompt_execution("anomaly_prompt", v2_text)

    # Rollback to v1.0
    reverted = registry.revert_prompt("anomaly_prompt", to_version="v1.0")
    assert reverted.version == "v1.0"
    assert registry.get_active_prompt("anomaly_prompt").version == "v1.0"

    # Now v1_text is valid, v2_text is rejected
    registry.validate_prompt_execution("anomaly_prompt", v1_text)
    with pytest.raises(PromptDigestMismatchError):
        registry.validate_prompt_execution("anomaly_prompt", v2_text)
