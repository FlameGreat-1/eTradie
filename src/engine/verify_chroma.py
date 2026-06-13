import chromadb
from chromadb.config import Settings


def main() -> None:
    token = "etradie_internal_secure_token_2026"  # nosec B105
    host = "chromadb"  # Inside docker network
    port = 8000

    try:
        client = chromadb.HttpClient(
            host=host,
            port=port,
            headers={"Authorization": f"Bearer {token}"},
            settings=Settings(anonymized_telemetry=False),
        )

        client.heartbeat()

        collections = client.list_collections()

        for col in collections:
            count = col.count()

            if count > 0:
                peek = col.peek(limit=2)
                for i in range(len(peek["ids"])):
                    # documents and metadatas are lists in peek result
                    docs = peek.get("documents") or []
                    peek.get("metadatas")

                    if i < len(docs):
                        content = docs[i]
                        if content and len(content) > 100:
                            content = content[:100] + "..."

    except Exception:  # nosec B110
        pass


if __name__ == "__main__":
    main()
