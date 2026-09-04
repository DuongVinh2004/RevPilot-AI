"""
RevPilot AI — Cryptographic Approval Digest Hasher
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §1.1 Invariant 1, §3.1
Conforms to INV-ACT-002, AC-008, and ADR-0003.
"""

from __future__ import annotations
import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any


class ApprovalDigestHasher:
    """
    Cryptographic SHA-256 hasher binding canonical action payloads, targets, and costs
    to unforgeable approval manifests (INV-ACT-002).
    """

    @staticmethod
    def compute_payload_digest(
        action_type: str,
        target_entities: list[str],
        payload: dict[str, Any],
        cost_usd: Decimal,
    ) -> str:
        """
        Produce deterministic SHA-256 hex digest over canonical action representation.
        Any modification to parameters, target references, or cost changes the digest.
        """
        canonical = {
            "action_type": action_type.strip(),
            "cost_usd": str(cost_usd),
            "payload": payload,
            "target_entities": sorted(list(target_entities)),
        }
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def verify_payload_digest(
        cls,
        expected_digest: str,
        action_type: str,
        target_entities: list[str],
        payload: dict[str, Any],
        cost_usd: Decimal,
    ) -> bool:
        """
        Constant-time verification of payload digest against expected digest.
        """
        actual_digest = cls.compute_payload_digest(
            action_type=action_type,
            target_entities=target_entities,
            payload=payload,
            cost_usd=cost_usd,
        )
        return hmac.compare_digest(actual_digest, expected_digest)

    @staticmethod
    def compute_policy_digest(policy_rules: Any) -> str:
        """
        Produce deterministic SHA-256 hex digest over active policy configuration.
        """
        if isinstance(policy_rules, str):
            canonical_json = json.dumps({"policy": policy_rules.strip()}, sort_keys=True)
        elif isinstance(policy_rules, (dict, list)):
            canonical_json = json.dumps(policy_rules, sort_keys=True, separators=(",", ":"))
        else:
            canonical_json = json.dumps({"policy": str(policy_rules)}, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
