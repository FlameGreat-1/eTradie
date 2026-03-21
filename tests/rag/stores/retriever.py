"""Tests for Retriever (vector store query + embedding).

Production module: src/engine/rag/retrieval/retriever.py

The Retriever requires async dependencies (BaseVectorStore,
BaseEmbeddingProvider) that need real or mock infrastructure.
These tests verify the import chain and model structure.
Full integration tests are deferred to the integration phase.
"""

from uuid import uuid4

from engine.rag.models.retrieval import RetrievedChunk


class TestRetrieverImports:
    def test_retriever_importable(self):
        """Retriever can be imported without side effects."""
        from engine.rag.retrieval.retriever import Retriever
        assert Retriever is not None

    def test_vector_store_base_importable(self):
        from engine.rag.vectorstore.base import BaseVectorStore
        assert BaseVectorStore is not None

    def test_embedding_base_importable(self):
        from engine.rag.embeddings.base import BaseEmbeddingProvider
        assert BaseEmbeddingProvider is not None


class TestRetrievedChunkModel:
    def test_construction(self):
        """RetrievedChunk can be constructed with all required fields."""
        chunk = RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            doc_type="master_rulebook",
            content="Rule 1: Always follow the trend.",
            score=0.92,
            rank=0,
            section="rules",
            subsection="entry",
            metadata={"framework": "SMC"},
        )
        assert chunk.score == 0.92
        assert chunk.rank == 0
        assert chunk.doc_type == "master_rulebook"
        assert chunk.section == "rules"

    def test_optional_fields(self):
        """Section and subsection are optional."""
        chunk = RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            doc_type="generic",
            content="Some content",
            score=0.5,
            rank=1,
        )
        assert chunk.section is None
        assert chunk.subsection is None
        assert chunk.metadata == {}

    def test_score_preserved(self):
        """Score is stored as-is (reranker may override later)."""
        chunk = RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            doc_type="smc_framework",
            content="BMS detection rules",
            score=0.1,
            rank=99,
        )
        assert chunk.score == 0.1
        assert chunk.rank == 99
