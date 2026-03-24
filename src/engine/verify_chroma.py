import chromadb
from chromadb.config import Settings


def main():
    token = "etradie_internal_secure_token_2026"
    host = "chromadb"  # Inside docker network
    port = 8000

    print(f"Connecting to ChromaDB at {host}:{port}...")
    try:
        client = chromadb.HttpClient(
            host=host,
            port=port,
            headers={"Authorization": f"Bearer {token}"},
            settings=Settings(anonymized_telemetry=False),
        )

        heartbeat = client.heartbeat()
        print(f"Heartbeat: {heartbeat}")

        collections = client.list_collections()
        print(f"\nFound {len(collections)} collections:")

        for col in collections:
            count = col.count()
            print(f"- {col.name}: {count} documents")

            if count > 0:
                print(f"  Previewing first 2 documents in '{col.name}':")
                peek = col.peek(limit=2)
                for i in range(len(peek["ids"])):
                    print(f"    ID: {peek['ids'][i]}")
                    print(f"    Metadata: {peek['metadatas'][i]}")
                    # documents and metadatas are lists in peek result
                    docs = peek.get("documents", [])
                    metas = peek.get("metadatas", [])

                    if i < len(docs):
                        content = docs[i]
                        if len(content) > 100:
                            content = content[:100] + "..."
                        print(f"    Content: {content}")
                    print("-" * 20)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
