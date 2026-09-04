"""
RevPilot AI — Compliance Evidence Cryptographic Signer
Specification: docs/25-compliance/COMPLIANCE-EVIDENCE-RUNBOOK.md §6.1, §6.2
Conforms to INV-AUD-001, ADR-0010, and AC-P08-007-01.
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path


class EvidenceSigner:
    """
    Cryptographic signer and hasher for compliance evidence artifacts and manifests.
    Provides SHA-256 digesting and tamper-evident signing.
    """

    DEFAULT_KEY: str = "revpilot_compliance_vault_master_hmac_secret_key_v1"

    @staticmethod
    def compute_file_sha256(filepath: Path | str) -> str:
        """Compute SHA-256 hexadecimal digest of a file."""
        p = Path(filepath)
        hasher = hashlib.sha256()
        with p.open("rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def compute_bytes_sha256(data: bytes) -> str:
        """Compute SHA-256 hexadecimal digest of raw bytes."""
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def sign_payload(cls, payload_bytes: bytes, key: str | None = None) -> str:
        """Generate HMAC-SHA256 signature over manifest bytes."""
        secret = (key or cls.DEFAULT_KEY).encode("utf-8")
        mac = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
        return f"sig_sha256:{mac}"

    @classmethod
    def verify_signature(cls, payload_bytes: bytes, signature: str, key: str | None = None) -> bool:
        """Verify HMAC-SHA256 signature in constant time."""
        expected = cls.sign_payload(payload_bytes, key=key)
        return hmac.compare_digest(expected, signature)
