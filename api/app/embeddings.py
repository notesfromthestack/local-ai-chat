from typing import List
from sentence_transformers import SentenceTransformer

from api.app.config import settings

import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.model_name = settings.embedding_model
        self.device = settings.embedding_device
        self.model = None

    def load(self):
        """Load the embedding model."""
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        logger.info(f"Embedding model loaded on {self.device}")

    @property
    def dim(self) -> int:
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        return self.model.get_sentence_embedding_dimension()

    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Each text is truncated to the model's max sequence length by the
        tokenizer, so oversized chunks won't silently lose their tails.
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()


# Global instance
embedding_service = EmbeddingService()
