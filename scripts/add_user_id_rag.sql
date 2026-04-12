ALTER TABLE rag_retrieval_logs DROP COLUMN IF EXISTS user_id;
ALTER TABLE rag_retrieval_logs ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT '';
