-- Initialize PostgreSQL with pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE mlauditor_db TO mlauditor;
GRANT ALL ON SCHEMA public TO mlauditor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mlauditor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mlauditor;
