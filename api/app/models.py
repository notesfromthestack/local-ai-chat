from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="User query to retrieve relevant chunks for.")
    top_k: Optional[int] = Field(default=5, description="Max number of chunks to retrieve.")
    score_threshold: Optional[float] = Field(
        default=None, description="Minimum similarity score to keep a chunk."
    )

class RAGQueryResponse(BaseModel):
    query: str = Field(..., description="User query that triggered retrieval.")
    answer: str = Field(..., description="LLM answer or fallback when no context is available.")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved documents with scores and metadata for source attribution.",
    )
    retrieved_count: int = Field(..., ge=0, description="Number of chunks passing the threshold.")
    

class RAGIndexRequest(BaseModel):
    texts: List[str] = Field(
        ..., description="List of text chunks to be embedded and indexed."
    )
    metadata: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional list of metadata dictionaries corresponding to each text chunk.",
    )

class RAGIndexResponse(BaseModel):
    indexed_count: int = Field(
        ..., ge=0, description="The total number of text chunks successfully indexed."
    )
    collection: str = Field(
        ..., description="The name of the vector database collection used."
    )
    message: str = Field(
        ..., description="A status message describing the outcome of the operation."
    )

class ChatMessage(BaseModel):
    role: str
    content: str


# OpenAI API Models
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    top_p: Optional[float] = 1.0


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


# Ollama API Models
class OllamaMessage(BaseModel):
    role: str
    content: str


class OllamaChatRequest(BaseModel):
    model: str
    messages: List[OllamaMessage]
    stream: bool = False
    options: Optional[Dict[str, Any]] = None


class OllamaChatResponse(BaseModel):
    model: str
    created_at: str
    message: OllamaMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
