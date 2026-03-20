from chromadb.api.models.Collection import Collection

from engine.rag.stores.retriever import ChromaRetriever


class MockChromaCollection:
    def __init__(self, name="test"):
        self.name = name
        self.count_val = 100
        self.queried = False
        
    def count(self):
        return self.count_val
        
    def query(self, query_texts, n_results, include):
        self.queried = True
        return {
            "ids": [["doc1", "doc2"]],
            "distances": [[0.1, 0.5]],  # Lower distance = higher similarity
            "metadatas": [[{"section": "rules"}, {"section": "guidelines"}]],
            "documents": [["Rule 1 text", "Guideline text"]]
        }


def test_retriever_query_success():
    """Test retrieving documents converts distances into relevance scores correctly."""
    mock_collection = MockChromaCollection()
    # We cheat the typing for testing
    retriever = ChromaRetriever(collection=None)
    retriever._collection = mock_collection
    
    results = retriever.retrieve("What is the rule?", top_k=2)
    
    assert len(results) == 2
    assert results[0].doc_id == "doc1"
    assert results[0].score == 0.9  # 1.0 - distance 0.1
    assert results[1].doc_id == "doc2"
    assert results[1].score == 0.5  # 1.0 - distance 0.5


def test_retriever_score_thresholding():
    """Test that documents with scores below threshold are dropped."""
    mock_collection = MockChromaCollection()
    retriever = ChromaRetriever(collection=None)
    retriever._collection = mock_collection
    
    results = retriever.retrieve("What is the rule?", top_k=2, min_score=0.7)
    
    # Only doc1 (score 0.9) passes the 0.7 threshold. doc2 (score 0.5) fails.
    assert len(results) == 1
    assert results[0].doc_id == "doc1"


def test_retriever_returns_empty_when_collection_empty():
    """Test early return when collection has 0 documents."""
    mock_collection = MockChromaCollection()
    mock_collection.count_val = 0
    
    retriever = ChromaRetriever(collection=None)
    retriever._collection = mock_collection
    
    results = retriever.retrieve("Any rules?", top_k=5)
    
    assert len(results) == 0
    assert getattr(mock_collection, "queried", False) is False
