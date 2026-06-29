import json
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

class MemoryStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="data/chroma")
        self.collection = self.client.get_or_create_collection(
            name="research_memory",
            embedding_function=DefaultEmbeddingFunction() # type: ignore
        )

    def _parse_sources(self, meta: dict) -> list:
        """Safely extract sources from metadata."""
        raw = meta.get("sources", "[]")
        try:
            return json.loads(str(raw))  # str() cast fixes Pylance
        except (json.JSONDecodeError, TypeError):
            return []

    def save(self, query: str, report: str, sources: list):
        try:
            existing = self.collection.get(ids=[query])
            if existing and existing["ids"]:
                print("Query already in memory — updating.")
                self.collection.update(
                    ids=[query],
                    documents=[query],
                    metadatas=[{
                        "report": str(report),
                        "sources": json.dumps(sources)
                    }]
                )
            else:
                self.collection.add(
                    ids=[query],
                    documents=[query],
                    metadatas=[{
                        "report": str(report),
                        "sources": json.dumps(sources)
                    }]
                )
            print(f"Memory saved: {query}")
        except Exception as e:
            print(f"Memory save failed: {e}")

    def find(self, query: str, threshold: float = 0.85) -> dict | None:
        try:
            if self.collection.count() == 0:
                print("Memory is empty.")
                return None

            results = self.collection.query(
                query_texts=[query],
                n_results=1
            )

            if not results:
                return None

            ids       = results.get("ids")       or []
            distances = results.get("distances") or []
            metadatas = results.get("metadatas") or []
            documents = results.get("documents") or []

            if not ids or not ids[0]:
                return None
            if not distances or not distances[0]:
                return None
            if not metadatas or not metadatas[0]:
                return None
            if not documents or not documents[0]:
                return None

            similarity = 1 - float(distances[0][0])
            print(f"Memory similarity score: {similarity:.2f}")

            if similarity >= threshold:
                meta = dict(metadatas[0][0])
                print(f"Memory HIT — score {similarity:.2f}")
                return {
                    "query":   str(documents[0][0]),
                    "report":  str(meta.get("report", "")),
                    "sources": self._parse_sources(meta)
                }

            print(f"Memory MISS — score {similarity:.2f} below threshold {threshold}")
            return None

        except Exception as e:
            print(f"Memory find failed: {e}")
            return None

    def _read_all(self) -> list:
        try:
            results = self.collection.get()
            if not results:
                return []

            documents = results.get("documents") or []
            metadatas = results.get("metadatas") or []

            if not documents or not metadatas:
                return []

            output = []
            for i, doc in enumerate(documents):
                meta = dict(metadatas[i])
                output.append({
                    "query":   str(doc),
                    "report":  str(meta.get("report", "")),
                    "sources": self._parse_sources(meta)
                })
            return output

        except Exception as e:
            print(f"Memory read failed: {e}")
            return []


memory = MemoryStore()