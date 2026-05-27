-- eTradie Engine — PostgreSQL Initialization
-- Executed once on first container start.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- The application database is created by the postgres entrypoint
-- from POSTGRES_DB. Alembic migrations manage all table creation.
-- Audit ref: D-C4.

