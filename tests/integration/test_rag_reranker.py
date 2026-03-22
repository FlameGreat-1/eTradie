from uuid import uuid4
import pytest
from engine.config import RAGConfig
from engine.rag.constants import DocumentType
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.reranker import Reranker

pytestmark = pytest.mark.integration

def _chunk(doc_type=DocumentType.MASTER_RULEBOOK, score=0.8, section=None, subsection=None):
    return RetrievedChunk(chunk_id=uuid4(), document_id=uuid4(), doc_type=doc_type, content="Test", score=score, rank=0, section=section, subsection=subsection, metadata={})

@pytest.fixture
def reranker():
    cfg = RAGConfig(enabled=False, embedding_provider="openai", embedding_model="text-embedding-3-large", openai_api_key="sk-test", chroma_host="localhost", chroma_port=8000, retrieval_top_k=10, rerank_enabled=True, rerank_top_k=5, ingest_on_startup=False)
    return Reranker(config=cfg)

class TestDocTypeBoost:
    def test_rulebook_outranks_generic(self, reranker):
        ranked = reranker.rerank([_chunk("generic", 0.85), _chunk(DocumentType.MASTER_RULEBOOK, 0.70)])
        assert ranked[0].doc_type == DocumentType.MASTER_RULEBOOK

    def test_smc_boosted(self, reranker):
        ranked = reranker.rerank([_chunk("generic", 0.80), _chunk(DocumentType.SMC_FRAMEWORK, 0.65)])
        assert ranked[0].doc_type == DocumentType.SMC_FRAMEWORK

class TestTruncation:
    def test_capped(self, reranker):
        assert len(reranker.rerank([_chunk(score=0.9-i*0.05) for i in range(10)], top_k=3)) == 3

    def test_ordering(self, reranker):
        ranked = reranker.rerank([_chunk(score=0.5), _chunk(score=0.9), _chunk(score=0.7)])
        assert [c.score for c in ranked] == sorted([c.score for c in ranked], reverse=True)

class TestSectionBonus:
    def test_bonus(self, reranker):
        ranked = reranker.rerank([_chunk("generic", 0.80), _chunk("generic", 0.80, "rules", "entry")])
        assert ranked[0].section == "rules"

class TestRanks:
    def test_sequential(self, reranker):
        ranked = reranker.rerank([_chunk(score=0.9-i*0.1) for i in range(5)])
        assert [c.rank for c in ranked] == list(range(len(ranked)))
