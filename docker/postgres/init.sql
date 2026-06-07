-- eTradie Engine — PostgreSQL Initialization
-- Executed once on first container start.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Least-privilege hardening (CHECKLIST Tier 7: principle of least
-- privilege). The official postgres entrypoint creates the role named
-- by POSTGRES_USER as a SUPERUSER and runs this script AS that role.
-- A superuser connection string in any one service means a single
-- leaked credential can drop tables, erase the audit trail, create new
-- roles, read every broker credential, and bypass row-level security.
--
-- We strip the dangerous role attributes in place. The role stays the
-- OWNER of the application database and of every object it creates, so
-- each service can still run its idempotent startup DDL (the Go
-- SchemaSQL() bodies and the engine's Alembic migrations) and the
-- SECURITY DEFINER maintenance functions keep executing as this owner.
-- It simply can no longer act as a cluster superuser.
--
-- A role is allowed to drop its own superuser attribute, so this runs
-- correctly even though the entrypoint executes the script as the role
-- itself. current_user is the POSTGRES_USER role; we target it by name
-- so the statement is independent of whatever POSTGRES_USER is set to.
DO $$
BEGIN
    EXECUTE format(
        'ALTER ROLE %I NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS',
        current_user
    );
END
$$;

-- The application database is created by the postgres entrypoint
-- from POSTGRES_DB. Alembic migrations manage all table creation.
-- Audit ref: D-C4.
