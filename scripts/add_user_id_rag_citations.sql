ALTER TABLE rag_analysis_citations DROP COLUMN IF EXISTS user_id;
ALTER TABLE rag_analysis_citations ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT '';
