from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    chunk_id: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)
    content: str = ""


class BaseVectorStore(ABC):
    @abstractmethod
    async def create_collection(self, name: str, *, dimensions: int) -> None:
        ...

    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        ...

    @abstractmethod
    async def upsert(
        self,
        collection: str,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        ...

    @abstractmethod
    async def delete(self, collection: str, *, ids: list[str]) -> None:
        ...

    @abstractmethod
    async def query(
        self,
        collection: str,
        *,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        ...

    @abstractmethod
    async def count(self, collection: str) -> int:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...
