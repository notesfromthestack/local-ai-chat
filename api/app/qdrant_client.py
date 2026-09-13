import hashlib
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from api.app.config import settings
import logging

logger = logging.getLogger(__name__)

# Stable namespace for deterministic point IDs.
_ID_NAMESPACE = uuid.UUID("6f1b8a7c-2d3e-4f5a-8b9c-0d1e2f3a4b5c")


class VectorStore:
    def __init__(self):
        self.url = settings.qdrant_url
        self.collection_name = settings.qdrant_collection
        self.client = None

    def connect(self, vector_size: int):
        """Connect to Qdrant and ensure collection exists at the given vector size."""
        logger.info(f"Connecting to Qdrant at {self.url}")
        self.client = QdrantClient(url=self.url)

        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            logger.info(
                f"Creating collection {self.collection_name} (size={vector_size})"
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        else:
            logger.info(f"Collection {self.collection_name} already exists")

    def add_documents(
        self, texts: List[str], vectors: List[List[float]], metadata: List[Dict[str, Any]]
    ):
        """Upsert documents. IDs are derived from (source, chunk_index, text) so
        re-indexing the same content is idempotent instead of duplicating."""
        if not (len(texts) == len(vectors) == len(metadata)):
            raise ValueError(
                f"texts/vectors/metadata length mismatch: "
                f"{len(texts)}/{len(vectors)}/{len(metadata)}"
            )

        points = [
            PointStruct(
                id=self._point_id(text, meta),
                vector=vec,
                payload={"text": text, **meta},
            )
            for text, vec, meta in zip(texts, vectors, metadata)
        ]

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"Upserted {len(points)} documents to {self.collection_name}")

    @staticmethod
    def _point_id(text: str, metadata: Dict[str, Any]) -> str:
        source = str(metadata.get("source", ""))
        chunk_index = str(metadata.get("chunk_index", ""))
        digest = hashlib.sha1(
            f"{source}|{chunk_index}|{text}".encode("utf-8")
        ).hexdigest()
        return str(uuid.uuid5(_ID_NAMESPACE, digest))

    def search(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
        ).points

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
            }
            for hit in results
        ]


# Global instance
vector_store = VectorStore()
