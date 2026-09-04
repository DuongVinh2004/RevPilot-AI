-- RevPilot AI — Local Development Database Initialization
-- Conforms to docs/27-database/DATABASE-SCHEMA.md and ADR-0004 / ADR-0005

-- Enable required core PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Create application least-privilege runtime role if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'revpilot_app') THEN
      CREATE ROLE revpilot_app WITH LOGIN PASSWORD 'placeholder_dev_pw';
   END IF;
END
$do$;

-- Create schema and grant permissions
CREATE SCHEMA IF NOT EXISTS revpilot AUTHORIZATION revpilot_app;
GRANT ALL ON SCHEMA revpilot TO revpilot_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA revpilot GRANT ALL ON TABLES TO revpilot_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA revpilot GRANT ALL ON SEQUENCES TO revpilot_app;

-- Baseline session context helper for Row-Level Security (RLS) enforcement
CREATE OR REPLACE FUNCTION revpilot.current_tenant_id() RETURNS TEXT AS $$
    SELECT NULLIF(current_setting('revpilot.tenant_id', true), '')::TEXT;
$$ LANGUAGE SQL STABLE;

-- Ensure public schema does not allow unrestricted creation
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
