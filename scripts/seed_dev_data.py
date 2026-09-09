"""
RevPilot AI — Development Data Seeder (Track 1 / T1-015)
Seeds baseline development data into PostgreSQL database.
Creates:
- Development Tenant (ten_dev_001)
- Default Organization (org_dev_001)
- Platform / Tenant Admin Principal (usr_admin_001)
- Membership linking Admin to Tenant with SYSTEM_ADMIN role
- 2 Canonical Customers with subscriptions
- 2 Realistic Anomaly Records with localizations
- 2 Pending Approval Requests (Tier 2 and Tier 3)
"""
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import asyncpg


async def seed_data() -> int:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://revpilot_app:placeholder_dev_pw@localhost:5432/revpilot_db"
    )
    # asyncpg expects postgresql:// or postgres://
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    print("Connecting to database to seed dev data...")
    try:
        conn = await asyncpg.connect(database_url)
    except Exception as exc:
        print(f"Connection failed: {exc}. Note: Seed requires running PostgreSQL instance.")
        return 1

    try:
        now = datetime.now(timezone.utc)
        as_of = now - timedelta(hours=1)
        tenant_id = "tnt_dev_001"

        # 1. Seed Tenant (Platform-scoped, bypasses RLS)
        await conn.execute("""
            INSERT INTO revpilot.tenants (id, name, slug, tier, status, config, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, status = EXCLUDED.status;
        """, tenant_id, "RevPilot Enterprise Dev", "revpilot-dev", "ENTERPRISE", "ACTIVE", json.dumps({"region": "ap-southeast-1"}), now)
        print(f"Seeded Tenant: {tenant_id}")

        # Set tenant session context for RLS-protected tables
        await conn.execute("SET revpilot.is_system = 'true';")
        await conn.execute("SELECT set_config('revpilot.current_tenant_id', $1, false);", tenant_id)

        # 2. Seed Organization
        await conn.execute("""
            INSERT INTO revpilot.organizations (tenant_id, id, name, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $5)
            ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, "org_dev_001", "Acme Enterprise Corp", "ACTIVE", now)
        print("Seeded Organization: org_dev_001")

        # 3. Seed Entitlements
        await conn.execute("""
            INSERT INTO revpilot.entitlements (tenant_id, id, plan_id, token_quota_monthly, connector_limit, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
            ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, "ent_001", "plan_enterprise", 100000000, 10, "ACTIVE", now)

        # 4. Seed Admin Principal
        admin_id = "usr_admin_001"
        await conn.execute("""
            INSERT INTO revpilot.principals (tenant_id, id, principal_type, email, display_name, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
            ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, admin_id, "USER", "admin@revpilot.dev", "Duong Vinh", "ACTIVE", now)
        print(f"Seeded Admin Principal: {admin_id}")

        # 5. Seed Membership
        await conn.execute("""
            INSERT INTO revpilot.memberships (tenant_id, id, principal_id, organization_id, role_name, granted_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, "mem_001", admin_id, "org_dev_001", "SYSTEM_ADMIN", now)

        # 6. Seed Customers
        cust_1 = "cust_alpha"
        dedup_key = f"{tenant_id}:salesforce:sf_alpha_01:{now}"
        await conn.execute("""
            INSERT INTO revpilot.canonical_customers (
                tenant_id, id, schema_version, source_system, source_id, name, email,
                segment, account_tier, billing_country, contract_mrr_cents, currency, status,
                event_time, effective_from, lineage_trace_id, dedup_key
            ) VALUES (
                $1, $2, '1.0.0', 'salesforce', 'sf_alpha_01', 'Alpha Global Tech', 'contact@alpha.com',
                'ENTERPRISE', 'TIER_1', 'US', 4500000, 'USD', 'ACTIVE',
                $3, $3, 'trace_seed_01', $4
            ) ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, cust_1, now, dedup_key)
        print(f"Seeded Customer: {cust_1}")

        # 7. Seed Anomalies
        anom_1 = "anom_01h8x8a7b3c1"
        hash_val = hashlib.sha256(f"{tenant_id}:{anom_1}:{now}".encode()).hexdigest()
        window_start = now - timedelta(days=7)
        await conn.execute("""
            INSERT INTO revpilot.anomaly_records (
                tenant_id, id, anomaly_type, metric_id, metric_version, detector_id, detector_version,
                observation_window_start, observation_window_end, event_time, effective_from, as_of_time,
                actual_value, expected_value, anomaly_score, severity, affected_scope, status, reproducibility_hash,
                created_at, updated_at
            ) VALUES (
                $1, $2, 'REVENUE_AT_RISK', 'METRIC_NET_MRR_EXPANSION', '1.0.0', 'DET-STL-RESIDUAL-001', '1.0.0',
                $3, $4, $4, $4, $5,
                -24.6000, 5.2000, 0.7820, 'CRITICAL', $6, 'DETECTED', $7,
                $4, $4
            ) ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, anom_1, window_start, now, as_of, json.dumps({"region": "US-EAST", "product": "Seats"}), hash_val)
        print(f"Seeded Anomaly: {anom_1}")

        # 8. Seed Pending Approvals
        appr_1 = "appr_01h8x9m2k4p8"
        appr_2 = "appr_01h8x9n1a9b2"
        p_digest_1 = hashlib.sha256(b"credit_voucher_alpha_2500").hexdigest()
        p_digest_2 = hashlib.sha256(b"carrier_sla_penalty_15400").hexdigest()
        pol_digest = hashlib.sha256(b"revpilot_action_policy_2026_09").hexdigest()
        expiry_1 = now + timedelta(hours=24)
        expiry_2 = now + timedelta(hours=4)

        await conn.execute("""
            INSERT INTO revpilot.approval_requests (
                tenant_id, id, action_type, target_entity_refs, payload_digest, policy_digest,
                estimated_cost_usd, required_approval_tier, status, expiry_time, correlation_id, created_at
            ) VALUES (
                $1, $2, 'ISSUE_SERVICE_CREDIT_VOUCHER', $3, $4, $5, 2500.00, 'TIER_2', 'PENDING',
                $6, 'corr_seed_appr_01', $7
            ) ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, appr_1, json.dumps(["cust_alpha", "sub_arr_450k"]), p_digest_1, pol_digest, expiry_1, now)

        await conn.execute("""
            INSERT INTO revpilot.approval_requests (
                tenant_id, id, action_type, target_entity_refs, payload_digest, policy_digest,
                estimated_cost_usd, required_approval_tier, status, expiry_time, correlation_id, created_at
            ) VALUES (
                $1, $2, 'OVERRIDE_CARRIER_SLA_PENALTY', $3, $4, $5, 15400.00, 'TIER_3', 'PENDING',
                $6, 'corr_seed_appr_02', $7
            ) ON CONFLICT (tenant_id, id) DO NOTHING;
        """, tenant_id, appr_2, json.dumps(["carrier_global", "contract_2025"]), p_digest_2, pol_digest, expiry_2, now)
        print("Seeded 2 Pending Approval Requests (Tier 2 & Tier 3)")

        # 9. Seed Default Dev Session
        dev_token_hash = hashlib.sha256(b"revpilot_dev_token_secret_2026").hexdigest()
        expiry_session = now + timedelta(days=365)
        await conn.execute("""
            INSERT INTO revpilot.sessions (
                tenant_id, id, principal_id, token_hash, issued_at, expires_at, is_active
            ) VALUES (
                $1, 'sess_dev_001', $2, $3, $4, $5, true
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET token_hash = EXCLUDED.token_hash, expires_at = EXCLUDED.expires_at;
        """, tenant_id, admin_id, dev_token_hash, now, expiry_session)
        print("Seeded Default Dev Session: sess_dev_001")

        print("Dev data seeding completed successfully.")
        return 0
    finally:
        await conn.close()


def main() -> int:
    try:
        return asyncio.run(seed_data())
    except Exception as exc:
        print(f"Fatal error seeding data: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
