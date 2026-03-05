-- eTradie Engine — PostgreSQL Initialization
-- Executed once on first container start.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Ensure the application database exists (Docker POSTGRES_DB handles this,
-- but we guard it here for manual setups).
SELECT 'CREATE DATABASE etradie'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'etradie')\gexec

-- Application schema lives inside the default public schema.
-- Alembic migrations manage all table creation.
