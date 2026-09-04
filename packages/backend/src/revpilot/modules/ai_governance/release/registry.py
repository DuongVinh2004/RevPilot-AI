"""
RevPilot AI — Prompt & Model Registry with Cryptographic Digest Pinning
Specification: docs/20-evaluation/MODEL-RELEASE-PROCESS.md §4
Conforms to INV-AI-001, AC-011, AC-P08-004-02.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.errors import DomainError
from revpilot.shared.temporal import UtcDateTime

logger = logging.getLogger(__name__)


class PromptDigestMismatchError(DomainError):
    """Untrusted prompt execution blocked due to digest mismatch (Status 403, Non-retryable)."""

    def __init__(
        self,
        message: str = "Untrusted prompt rejected",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PROMPT_DIGEST_MISMATCH",
            message=message,
            details=details,
            retryable=False,
        )
        self.status_code = 403


class PromptDefinition(BaseModel):
    """
    Immutable version-pinned prompt template registered in the platform registry.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    prompt_id: str
    template_name: str
    raw_template: str
    sha256_digest: str
    version: str
    registered_at: UtcDateTime
    author_principal: str
    status: str = "ACTIVE"


class PromptRegistryService:
    """
    Enforces immutable cryptographic SHA-256 digest validation (pr_sha256:...)
    for all agent personas and tool instruction prompts (INV-AI-001, AC-P08-004-02).
    """

    def __init__(self, audit_emitter: Any | None = None) -> None:
        self._audit_emitter = audit_emitter
        self._active_prompts: dict[str, PromptDefinition] = {}
        self._version_history: dict[tuple[str, str], PromptDefinition] = {}
        self._audit_events: list[dict[str, Any]] = []

    def _emit_audit(self, event_type: str, details: dict[str, Any]) -> None:
        event = {
            "event_id": f"aud_reg_{uuid4().hex}",
            "occurred_at": UtcDateTime.now().isoformat(),
            "event_type": event_type,
            "details": details,
        }
        self._audit_events.append(event)
        if self._audit_emitter and hasattr(self._audit_emitter, "emit"):
            self._audit_emitter.emit(event)
        logger.info("PROMPT_REGISTRY_AUDIT: %s: %s", event_type, details)

    @property
    def audit_events(self) -> list[dict[str, Any]]:
        return list(self._audit_events)

    @staticmethod
    def compute_digest(text: str) -> str:
        """Compute canonical pr_sha256:... digest from prompt text."""
        raw_bytes = text.strip().encode("utf-8")
        h = hashlib.sha256(raw_bytes).hexdigest()
        return f"pr_sha256:{h}"

    def register_prompt(
        self,
        template_name: str,
        raw_template: str,
        version: str = "v1.0",
        author_principal: str = "principal:ai-lead",
    ) -> PromptDefinition:
        """Register a new immutable prompt template with cryptographic digest."""
        digest = self.compute_digest(raw_template)
        prompt_id = f"prm_{uuid4().hex[:12]}"
        now = UtcDateTime.now()

        definition = PromptDefinition(
            prompt_id=prompt_id,
            template_name=template_name,
            raw_template=raw_template,
            sha256_digest=digest,
            version=version,
            registered_at=now,
            author_principal=author_principal,
            status="ACTIVE",
        )

        self._active_prompts[template_name] = definition
        self._version_history[(template_name, version)] = definition

        self._emit_audit(
            "PROMPT_REGISTERED",
            {
                "prompt_id": prompt_id,
                "template_name": template_name,
                "version": version,
                "digest": digest,
                "author": author_principal,
            },
        )
        return definition

    def validate_prompt_execution(
        self,
        template_name: str,
        candidate_prompt_text: str,
    ) -> PromptDefinition:
        """
        Validate that runtime prompt text matches registered SHA-256 digest exactly.
        Rejects unpinned or tampered prompts with 403 (AC-P08-004-02).
        """
        registered = self._active_prompts.get(template_name)
        if not registered:
            self._emit_audit(
                "UNREGISTERED_PROMPT_EXECUTION_ATTEMPT",
                {"template_name": template_name},
            )
            raise PromptDigestMismatchError(
                f"Untrusted prompt rejected: template '{template_name}' is not registered in registry",
                details={"template_name": template_name},
            )

        candidate_digest = self.compute_digest(candidate_prompt_text)
        if candidate_digest != registered.sha256_digest:
            self._emit_audit(
                "PROMPT_TAMPER_DETECTED",
                {
                    "template_name": template_name,
                    "expected_digest": registered.sha256_digest,
                    "candidate_digest": candidate_digest,
                },
            )
            raise PromptDigestMismatchError(
                f"Untrusted prompt rejected: digest mismatch for '{template_name}' "
                f"(expected={registered.sha256_digest}, computed={candidate_digest})",
                details={
                    "template_name": template_name,
                    "expected_digest": registered.sha256_digest,
                    "computed_digest": candidate_digest,
                },
            )

        return registered

    def get_active_prompt(self, template_name: str) -> PromptDefinition | None:
        return self._active_prompts.get(template_name)

    def revert_prompt(self, template_name: str, to_version: str) -> PromptDefinition:
        """Roll back active prompt template to a historical version (§6.2)."""
        key = (template_name, to_version)
        if key not in self._version_history:
            raise ValueError(f"Historical version '{to_version}' not found for template '{template_name}'")

        previous = self._version_history[key]
        self._active_prompts[template_name] = previous

        self._emit_audit(
            "PROMPT_REVERTED",
            {
                "template_name": template_name,
                "reverted_to_version": to_version,
                "digest": previous.sha256_digest,
            },
        )
        return previous
