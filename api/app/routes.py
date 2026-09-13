import logging
import time
import uuid
import html
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse

from api.app.config import settings

# Import unified models and schemas
from api.app.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    OllamaMessage,
)

# Import internal business logic services and vector stores
from api.app.ollama_client import OllamaClient
from api.app.embeddings import embedding_service
from api.app.document_processor import chunk_text
from api.app.qdrant_client import vector_store

# Import structured instrumentation metrics
from api.app.metrics import (
    CHAT_DURATION_SECONDS,
    CHAT_REQUESTS_TOTAL,
    CHAT_TOKENS_TOTAL,
    RAG_DOCUMENTS_RETRIEVED_TOTAL,
    RAG_DURATION_SECONDS,
    RAG_INDEX_DURATION_SECONDS,
    RAG_INDEX_REQUESTS_TOTAL,
    RAG_REQUESTS_TOTAL,
    metrics,
)

logger = logging.getLogger(__name__)
router = APIRouter()
ollama_client = OllamaClient()


async def _run_rag(
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> tuple[str, List[Dict[str, Any]], bool, Dict[str, int]]:
    """Shared retrieval + generation pipeline.

    Returns (answer, sources, had_context, token_usage). token_usage has keys
    prompt_tokens, completion_tokens, total_tokens.
    """
    top_k = top_k if top_k is not None else settings.rag_top_k
    score_threshold = (
        score_threshold
        if score_threshold is not None
        else settings.rag_score_threshold
    )

    query_vector = embedding_service.encode([query])[0]
    results = vector_store.search(query_vector, limit=top_k)
    filtered = [r for r in results if r["score"] >= score_threshold]

    sources: List[Dict[str, Any]] = [
        {
            "text": r["text"],
            "score": float(r["score"]),
            "metadata": r.get("metadata") or {},
        }
        for r in filtered
    ]

    if sources:
        context = "\n\n".join(
            f"Document {i}: {s['text']}" for i, s in enumerate(sources, start=1)
        )
        prompt = (
            "Answer the question based on the context below.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )
    else:
        prompt = query

    ollama_response = await ollama_client.chat(
        messages=[OllamaMessage(role="user", content=prompt)],
        temperature=getattr(settings, "temperature", 0.7),
    )
    answer = (ollama_response.message.content or "").strip()
    prompt_tokens = ollama_response.prompt_eval_count or 0
    completion_tokens = ollama_response.eval_count or 0
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    return answer, sources, bool(sources), usage


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint.

    Proxies incoming inference requests to Ollama and maps outputs back to standard schemas.
    """
    start_time = time.time()
    metrics.inc_counter(CHAT_REQUESTS_TOTAL)
    logger.info("Chat completion request received for model: %s", request.model)

    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages array must not be empty.")
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming is not yet supported on this interface.")

    ollama_messages = [
        ChatMessage(role=msg.role, content=msg.content)
        for msg in request.messages
    ]

    total_tokens = 0
    try:
        ollama_response = await ollama_client.chat(
            messages=ollama_messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        prompt_tokens = ollama_response.prompt_eval_count or 0
        completion_tokens = ollama_response.eval_count or 0
        total_tokens = prompt_tokens + completion_tokens

        response = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            object="chat.completion",
            created=int(start_time),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role=ollama_response.message.role,
                        content=ollama_response.message.content,
                    ),
                    finish_reason="stop",
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

        if total_tokens > 0:
            metrics.inc_counter(CHAT_TOKENS_TOTAL, total_tokens)

        logger.info("Chat completion transaction successful. Total tokens: %d", total_tokens)
        return response

    except Exception as e:
        logger.error("Chat completion system pipeline failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An upstream processing fault occurred during generation.")

    finally:
        metrics.observe_histogram(CHAT_DURATION_SECONDS, time.time() - start_time)


@router.post("/rag/index", response_model=RAGIndexResponse)
async def rag_index(request: RAGIndexRequest):
    """Embed the provided text chunks and upsert them into the vector store."""
    logger.info("RAG index request: %d chunks", len(request.texts))
    start_time = time.time()

    if not request.texts:
        raise HTTPException(status_code=400, detail="texts must not be empty.")

    metadata = request.metadata or [{} for _ in request.texts]
    if len(metadata) != len(request.texts):
        raise HTTPException(
            status_code=400,
            detail="metadata length must match texts length.",
        )

    try:
        vectors = embedding_service.encode(request.texts)
        vector_store.add_documents(
            texts=request.texts, vectors=vectors, metadata=metadata
        )

        return RAGIndexResponse(
            indexed_count=len(request.texts),
            collection=getattr(settings, "qdrant_collection", "documents"),
            message="ok",
        )
    except Exception as e:
        logger.error("RAG index failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Indexing failed.")
    finally:
        metrics.observe_histogram(RAG_INDEX_DURATION_SECONDS, time.time() - start_time)
        metrics.inc_counter(RAG_INDEX_REQUESTS_TOTAL)


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """Retrieval + Generation. Returns answer plus sources for attribution."""
    logger.info("RAG query: %s", request.query)
    start_time = time.time()
    metrics.inc_counter(RAG_REQUESTS_TOTAL)
    retrieved_count = 0

    try:
        answer, sources, had_context, usage = await _run_rag(
            request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )
        retrieved_count = len(sources)

        if not had_context or not answer:
            answer = "No information available"

        if usage["total_tokens"] > 0:
            metrics.inc_counter(CHAT_TOKENS_TOTAL, usage["total_tokens"])

        response = RAGQueryResponse(
            query=request.query,
            answer=answer,
            sources=sources,
            retrieved_count=retrieved_count,
        )
        # Attach usage on the response headers so JSON schema stays stable.
        return JSONResponse(
            content={**response.model_dump(), "usage": usage},
        )
    except Exception as e:
        logger.error("RAG pipeline failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="RAG pipeline hit a barrier while retrieving/generating.",
        )
    finally:
        metrics.observe_histogram(RAG_DURATION_SECONDS, time.time() - start_time)
        metrics.inc_counter(RAG_DOCUMENTS_RETRIEVED_TOTAL, retrieved_count)


def _render_sources_html(sources: List[Dict[str, Any]]) -> str:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for s in sources:
        key = (s.get("metadata") or {}).get("source", "unknown")
        grouped.setdefault(key, []).append(s)

    blocks = []
    for src, items in grouped.items():
        top_score = max(i["score"] for i in items)
        snippets = "".join(
            f"<li><div>{html.escape(i['text'][:400])}"
            f"{'…' if len(i['text']) > 400 else ''}</div>"
            f"<div style='color:#888;font-size:0.9em'>score: {i['score']:.4f}</div></li>"
            for i in sorted(items, key=lambda x: -x["score"])
        )
        blocks.append(
            f"<li><strong>{html.escape(src)}</strong> "
            f"<span style='color:#888'>({len(items)} chunk"
            f"{'s' if len(items) != 1 else ''}, top score {top_score:.4f})</span>"
            f"<ul>{snippets}</ul></li>"
        )

    return (
        f"<details class='sources'><summary>Sources "
        f"({len(grouped)} document{'s' if len(grouped) != 1 else ''}, "
        f"{len(sources)} chunk{'s' if len(sources) != 1 else ''})</summary>"
        f"<ul>{''.join(blocks)}</ul></details>"
    )


@router.post("/ui/query", response_class=HTMLResponse)
async def ui_query(query: str = Form("")):
    query = (query or "").strip()
    if not query:
        return HTMLResponse("<h3>Please enter a question.</h3>", status_code=200)

    start_time = time.time()
    metrics.inc_counter(RAG_REQUESTS_TOTAL)
    retrieved_count = 0

    try:
        answer, sources, had_context, usage = await _run_rag(query)
        retrieved_count = len(sources)
        answer = answer or "No information available"

        if usage["total_tokens"] > 0:
            metrics.inc_counter(CHAT_TOKENS_TOTAL, usage["total_tokens"])

        # Reference pricing: gpt-4o-mini as of 2025 ($0.15/M input, $0.60/M output).
        # Local inference is free; this is purely educational.
        estimated_cost = (
            usage["prompt_tokens"] * 0.15 + usage["completion_tokens"] * 0.60
        ) / 1_000_000
        cost_str = (
            f"${estimated_cost:.4f}" if estimated_cost >= 0.0001 else "<$0.0001"
        )
        tooltip = (
            f"On gpt-4o-mini this query would cost ~{cost_str} "
            f"({usage['prompt_tokens']} in × $0.15/M + "
            f"{usage['completion_tokens']} out × $0.60/M). "
            f"Running locally: free."
        )

        usage_html = (
            f"<p class='usage' style='color:#888;font-size:0.85rem;margin-top:0.75rem'>"
            f"🤖 <code>{html.escape(settings.ollama_model)}</code> · "
            f"<span class='tooltip' data-tip='{html.escape(tooltip)}'>"
            f"🧮 {usage['prompt_tokens']} prompt + "
            f"{usage['completion_tokens']} completion = "
            f"<strong>{usage['total_tokens']} tokens</strong>"
            f"</span>"
            f"</p>"
        )

        if had_context:
            sources_html = _render_sources_html(sources)
            body = (
                f"<div class='answer' data-md>{html.escape(answer)}</div>"
                f"{usage_html}"
                f"{sources_html}"
            )
        else:
            body = (
                f"<div class='answer' data-md>{html.escape(answer)}</div>"
                f"{usage_html}"
                "<p style='color:#666'>No relevant documents found; "
                "answered using general knowledge.</p>"
            )
        return HTMLResponse(body, status_code=200)

    except Exception as e:
        logger.error("UI query failed: %s", e, exc_info=True)
        return HTMLResponse(
            content=f"<h3>Error</h3><p>{html.escape(str(e))}</p>",
            status_code=200,
        )
    finally:
        metrics.observe_histogram(RAG_DURATION_SECONDS, time.time() - start_time)
        metrics.inc_counter(RAG_DOCUMENTS_RETRIEVED_TOTAL, retrieved_count)


@router.post("/ui/upload", response_class=HTMLResponse)
async def ui_upload(files: List[UploadFile] = File(...)):
    """Accept one or more markdown files, chunk + embed + index them."""
    if not files:
        return HTMLResponse("<p>No files uploaded.</p>", status_code=200)

    results: list[str] = []
    total_chunks = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024

    for f in files:
        name = f.filename or "unnamed.md"
        try:
            if not name.lower().endswith((".md", ".markdown", ".txt")):
                results.append(
                    f"<li>⚠️ {html.escape(name)} — skipped (not a .md/.txt file)</li>"
                )
                continue

            raw = await f.read()
            if len(raw) > max_bytes:
                results.append(
                    f"<li>❌ {html.escape(name)} — too large "
                    f"({len(raw) // 1024} KB > {settings.max_upload_mb} MB limit)</li>"
                )
                continue
            text = raw.decode("utf-8", errors="replace")
            if not text.strip():
                results.append(f"<li>⚠️ {html.escape(name)} — empty</li>")
                continue

            chunks = chunk_text(text)
            vectors = embedding_service.encode(chunks)
            metadata = [
                {"source": name, "chunk_index": i} for i in range(len(chunks))
            ]
            vector_store.add_documents(
                texts=chunks, vectors=vectors, metadata=metadata
            )

            total_chunks += len(chunks)
            results.append(
                f"<li>✅ {html.escape(name)} — {len(chunks)} chunk"
                f"{'s' if len(chunks) != 1 else ''} indexed</li>"
            )
        except Exception as e:
            logger.error("Upload failed for %s: %s", name, e, exc_info=True)
            results.append(
                f"<li>❌ {html.escape(name)} — error: {html.escape(str(e))}</li>"
            )

    summary = (
        f"<p><strong>Indexed {total_chunks} chunk"
        f"{'s' if total_chunks != 1 else ''} from {len(files)} file"
        f"{'s' if len(files) != 1 else ''}.</strong></p>"
    )
    return HTMLResponse(
        content=f"{summary}<ul>{''.join(results)}</ul>", status_code=200
    )
