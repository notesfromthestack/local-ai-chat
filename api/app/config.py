from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # Ollama Configuration
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"

    # Qdrant Configuration
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "documents"

    # Embedding Configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    # RAG Configuration
    rag_top_k: int = 5
    rag_score_threshold: float = 0.3
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50

    # Uploads
    max_upload_mb: int = 10

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
