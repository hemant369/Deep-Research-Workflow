import json
import logging
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


logger = logging.getLogger(__name__)

# Resolve relative to the backend package so the store does not depend on the CWD.
CHROMA_PATH = Path(__file__).resolve().parents[1] / "data" / "chroma"


class MemoryStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.client.get_or_create_collection(
            name="research_reports",
            embedding_function=DefaultEmbeddingFunction(),  # type: ignore
            metadata={"hnsw:space": "cosine"},
        )

    def save(self, query: str, report: str, results: list) -> None:
        try:
            self.collection.upsert(
                ids=[query],
                documents=[query],
                metadatas=[{"report": report, "results": json.dumps(results)}],
            )
            logger.info("Memory saved: %s", query)
        except Exception:
            logger.exception("Memory save failed")

    def find(self, query: str, threshold: float = 0.9) -> dict | None:
        """Return the closest saved report if its cosine similarity >= threshold."""
        try:
            if self.collection.count() == 0:
                return None

            found = self.collection.query(query_texts=[query], n_results=1)
            distances = (found.get("distances") or [[]])[0]
            metadatas = (found.get("metadatas") or [[]])[0]
            if not distances or not metadatas:
                return None

            similarity = 1 - float(distances[0])
            if similarity < threshold:
                logger.info("Memory miss (similarity %.2f)", similarity)
                return None

            meta = metadatas[0]
            logger.info("Memory hit (similarity %.2f)", similarity)
            return {
                "report": str(meta.get("report", "")),
                "results": json.loads(str(meta.get("results", "[]"))),
            }
        except Exception:
            logger.exception("Memory lookup failed")
            return None


memory = MemoryStore()
