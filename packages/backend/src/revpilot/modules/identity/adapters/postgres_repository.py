"""
RevPilot AI — PostgreSQL Identity and Authentication Adapter (Rail 3)
Implements AuthenticationPort against PostgreSQL revpilot.sessions and revpilot.principals.
Enforces INV-IAM-001, INV-TEN-002, and INV-REL-001.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
import asyncpg

from revpilot.modules.identity.domain.models import (
    AuthTokenClaims,
    VerifiedClaimsToken,
    PrincipalType,
)
from revpilot.modules.identity.domain.token_policy import VerifiedSessionEvidence
from revpilot.modules.identity.ports.authentication import AuthenticationPort
from revpilot.shared.errors import AuthenticationError, TenancyViolationError
from revpilot.shared.identifiers import TenantId, PrincipalId
from revpilot.shared.temporal import UtcDateTime


class PostgresAuthAdapter(AuthenticationPort):
    """
    PostgreSQL-backed authentication adapter verifying tokens and session lifecycle.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def async_verify_token(
        self,
        token: str,
        *,
        expected_issuer: str = "revpilot-idp",
        expected_audience: str = "revpilot-api",
        as_of: UtcDateTime | None = None,
    ) -> VerifiedClaimsToken:
        token_hash = self._hash_token(token)
        now = as_of or UtcDateTime.now()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Elevate to system context locally within transaction to query session token by hash under RLS (INV-TEN-002, INV-IAM-001)
                await conn.execute("SET LOCAL revpilot.is_system = 'true';")

                # Query session and principal
                query = """
                    SELECT
                        s.id as session_id,
                        s.tenant_id,
                        s.principal_id,
                        s.issued_at,
                        s.expires_at,
                        s.revoked_at,
                        s.is_active,
                        p.email,
                        p.principal_type,
                        p.status as principal_status
                    FROM revpilot.sessions s
                    JOIN revpilot.principals p ON s.tenant_id = p.tenant_id AND s.principal_id = p.id
                    WHERE s.token_hash = $1
                """
                row = await conn.fetchrow(query, token_hash)
                if not row:
                    raise AuthenticationError("Invalid or unknown authentication token", details={"error": "token_not_found"})

                if not row["is_active"] or row["revoked_at"] is not None:
                    raise AuthenticationError("Token session has been revoked", details={"session_id": row["session_id"]})

                expires_at = UtcDateTime.from_datetime(row["expires_at"])
                if now > expires_at:
                    raise AuthenticationError("Token session has expired", details={"session_id": row["session_id"]})

                if row["principal_status"] != "ACTIVE":
                    raise AuthenticationError(f"Principal is {row['principal_status']}", details={"principal_id": row["principal_id"]})

                # Fetch roles from memberships
                roles_rows = await conn.fetch(
                    "SELECT role_name FROM revpilot.memberships WHERE tenant_id = $1 AND principal_id = $2 AND revoked_at IS NULL",
                    row["tenant_id"],
                    row["principal_id"],
                )
                roles = frozenset([r["role_name"] for r in roles_rows])

                claims = AuthTokenClaims(
                    sub=row["principal_id"],
                    iss=expected_issuer,
                    aud=expected_audience,
                    exp=int(expires_at.as_datetime().timestamp()),
                    nbf=int(UtcDateTime.from_datetime(row["issued_at"]).as_datetime().timestamp()),
                    iat=int(UtcDateTime.from_datetime(row["issued_at"]).as_datetime().timestamp()),
                    tenant_id=row["tenant_id"],
                    roles=roles,
                    permissions=frozenset(),
                    email=row["email"],
                    is_system=row["principal_type"] == "SYSTEM",
                )

                provenance_payload = f"{token_hash}:{claims.sub}:{claims.tenant_id}:{claims.exp}"
                provenance_hash = hashlib.sha256(provenance_payload.encode()).hexdigest()

                return VerifiedClaimsToken(
                    claims=claims,
                    raw_token_digest=token_hash,
                    provenance_hash=provenance_hash,
                )

    async def async_revoke_session(self, session_id: str) -> None:
        now = UtcDateTime.now()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET LOCAL revpilot.is_system = 'true';")
                await conn.execute(
                    "UPDATE revpilot.sessions SET is_active = FALSE, revoked_at = $1 WHERE id = $2",
                    now.as_datetime(),
                    session_id,
                )

    def verify_token(
        self,
        token: str,
        *,
        expected_issuer: str = "revpilot-idp",
        expected_audience: str = "revpilot-api",
        as_of: UtcDateTime | None = None,
    ) -> VerifiedClaimsToken:
        import asyncio
        return asyncio.run(
            self.async_verify_token(
                token,
                expected_issuer=expected_issuer,
                expected_audience=expected_audience,
                as_of=as_of,
            )
        )

    def revoke_session(self, session_id: str) -> None:
        import asyncio
        asyncio.run(self.async_revoke_session(session_id))

    def get_session_evidence(
        self,
        session_id: str,
        as_of: UtcDateTime | None = None,
    ) -> VerifiedSessionEvidence:
        raise NotImplementedError("Use async session retrieval or in-memory verification.")
