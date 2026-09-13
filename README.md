# DocChat

A local Retrieval-Augmented Generation (RAG) chat app that runs entirely on your Mac. It combines:

- **FastAPI** — HTTP API + minimal htmx web UI
- **Ollama** — local LLM (default: `llama3.1:8b`)
- **Qdrant** — vector database for document embeddings
- **sentence-transformers** — text embeddings (`all-MiniLM-L6-v2`)

Everything runs in containers using **Podman** (no Docker Desktop required).

---

## Prerequisites

- macOS (Apple Silicon or Intel)
- [Homebrew](https://brew.sh/)
- ~10 GB free disk space (models + images)
- 8 GB+ RAM allocated to the Podman VM

## 1. Install Podman

```sh
brew install podman podman-compose
```

Initialize and start the VM (one-time setup):

```sh
podman machine init --cpus 4 --memory 8192 --disk-size 60
podman machine start
```

Verify:

```sh
podman info
```

> After a reboot, run `podman machine start` again before using the app.

## 2. Clone and configure

```sh
git clone <your-repo-url> ai-chat
cd ai-chat
cp .env.example .env
```

Edit `.env` if you want a different model or ports. Defaults work out of the box.

## 3. Build and start

```sh
make build
make up
```

First build takes a few minutes (downloads Python deps + embedding model).

## 4. Pull the LLM model

The `ollama` container starts empty. Pull the model referenced in `.env`:

```sh
make ollama-pull
```

This pulls `llama3.1:8b` by default (~5 GB, high quality). For a smaller/faster model, run:

```sh
podman compose exec ollama ollama pull llama3.2:1b
```

and set `OLLAMA_MODEL=llama3.2:1b` in your `.env`.

Verify:

```sh
make ollama-list
```

## 5. Open the app

- Web UI: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>
- Qdrant dashboard: <http://localhost:6334/dashboard>

## 6. Index some documents (optional)

Without indexed documents, the app answers from the LLM's general knowledge. To enable RAG, index PDFs or text using the scripts in [examples/](examples/).

These scripts run on your Mac (not inside a container), so they need their own Python environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then index a markdown file or a whole directory of them:

```sh
python examples/index_markdown.py path/to/notes.md
python examples/index_markdown.py path/to/docs_dir
```

> The main app itself does **not** need this — `make build` installs `requirements.txt` inside the API container automatically.

---

## Daily use

| Command | What it does |
| --- | --- |
| `make up` | Start all services in the background |
| `make down` | Stop all services |
| `make logs` | Tail logs from all services |
| `make logs-api` | Tail just the API logs |
| `make restart` | Restart all services |
| `make shell` | Open a shell inside the API container |
| `make test` | Run the pytest suite in the container |
| `make clean` | Stop everything and delete volumes (fresh start) |

After a reboot:

```sh
podman machine start
make up
```

To reclaim RAM when you're done:

```sh
make down
podman machine stop
```

### Hot reload

The API container runs `uvicorn --reload` and mounts `./api` from your host, so edits to Python files reload the API automatically — no `make restart` needed. Template (`.html`) changes are picked up on the next request, no reload needed at all.

Only Dockerfile changes or new `requirements.txt` entries require `make build`.

### Running tests locally (outside the container)

The container has all dependencies, but you can also run tests from your host once you've set up the venv (see [Indexing documents](#6-index-some-documents-optional)):

```sh
source .venv/bin/activate
pytest
```

`pyproject.toml` sets `pythonpath` so imports resolve.

---

## How it works (in plain English)

When you index a document, the app doesn't store the whole file as one blob. It breaks it into pieces so the AI can find just the *relevant* parts when you ask a question.

Here's the vocabulary:

- **Chunk** — a small slice of your document (a few paragraphs). One markdown file might turn into 5, 20, or 100 chunks depending on how long it is.
- **Embedding** — a list of 384 numbers that represents the *meaning* of a chunk. Two chunks about "installing Podman" will have similar numbers, even if they use different words. Think of it as a fingerprint for meaning.
- **Point** — Qdrant's word for one row in the database. Each point holds **one chunk** plus its embedding plus some info about where it came from (`source`, `chunk_index`).

So: **1 point = 1 chunk = 1 searchable piece of your document.**

If the Qdrant dashboard says "42 points," you have 42 chunks indexed across all your files.

When you ask a question:
1. Your question gets turned into an embedding (the same 384 numbers).
2. Qdrant finds the points whose embeddings are closest to your question's embedding — those are the most relevant chunks.
3. Those chunks get handed to the AI, which uses them to write an answer.

That's the whole RAG trick: retrieve relevant chunks, then let the AI answer using them as context.

---

## Configuration

All settings live in `.env` — see [.env.example](.env.example) for the full list. Highlights:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_MODEL` | `llama3.1:8b` | Which model the API asks Ollama to run |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model for RAG |
| `RAG_TOP_K` | `5` | Number of chunks retrieved per query |
| `RAG_SCORE_THRESHOLD` | `0.3` | Minimum similarity score to include a chunk |
| `API_PORT` | `8000` | Host port for the web UI / API |

Change any value and `make restart` to apply.

### Tuning the RAG knobs

The four `RAG_*` values control how documents get sliced up and how many chunks feed the AI. In plain English:

**`RAG_CHUNK_SIZE=512`** — Max size of one chunk, in characters (roughly ~100 words).
- **Smaller** (e.g. `256`): more chunks, more precise matches, but each chunk has less context. The AI might miss the "big picture."
- **Larger** (e.g. `1024`): fewer chunks, more context per match, but retrieval gets fuzzier because each chunk covers more topics.
- Think: sentence-level vs. paragraph-level vs. page-level.

**`RAG_CHUNK_OVERLAP=50`** — How many characters neighboring chunks share.
- Without overlap, a sentence that gets split at the chunk boundary is lost from both chunks. Overlap is like giving each chunk a little "runway" from the previous one so ideas don't get chopped in half.
- Rule of thumb: 10–20% of `RAG_CHUNK_SIZE`.

**`RAG_TOP_K=5`** — How many chunks Qdrant returns per query.
- **Higher** (e.g. `10`): more context for the AI, but noisier — irrelevant chunks may sneak in and confuse the answer. Also slower.
- **Lower** (e.g. `3`): tighter, faster answers, but the AI might miss info that was in chunk #4.

**`RAG_SCORE_THRESHOLD=0.3`** — Minimum similarity score (0–1) a chunk needs to be kept.
- Every chunk gets a score for how "close in meaning" it is to your question. `1.0` = identical meaning, `0.0` = totally unrelated.
- **Higher** (e.g. `0.6`): only very confident matches make it through. Great when you have lots of documents; risky when you have few (you may get zero matches and the AI falls back to general knowledge).
- **Lower** (e.g. `0.1`): almost everything passes. Useful when your embedding scores tend to be small, but you'll get more junk in the sources.

**What do the scores actually mean?**

For the default `all-MiniLM-L6-v2` embedding model, here's a rough interpretation of the cosine similarity scores you'll see in the "Sources" panel:

| Score | Meaning |
| --- | --- |
| **0.75+** | Nearly identical topic — probably a direct answer to your question |
| **0.55 – 0.75** | Relevant — same domain, mentions the right concepts |
| **0.40 – 0.55** | Loosely related — same broad area, may or may not help |
| **0.25 – 0.40** | Weak — probably not useful, but could catch tangential context |
| **< 0.25** | Unrelated noise |

Rules of thumb:
- If your top result is **0.8+**, retrieval nailed it and the answer should be well-grounded.
- If you're mostly seeing scores in the **0.5–0.6 range**, retrieval is working reasonably.
- If your top result is only in the **0.4s**, the document probably doesn't cover the question well — the AI is guessing.
- Absolute scores are model-specific. What's "good" for `all-MiniLM-L6-v2` won't match numbers from a different embedding model.
- The *relative* ranking of chunks matters more than any absolute cutoff.

**Quick starter recipes:**

| Goal | Settings |
| --- | --- |
| Short FAQ-style docs | `CHUNK_SIZE=256`, `OVERLAP=25`, `TOP_K=3`, `THRESHOLD=0.5` |
| Long articles / books | `CHUNK_SIZE=1024`, `OVERLAP=100`, `TOP_K=5`, `THRESHOLD=0.3` |
| Code / technical docs | `CHUNK_SIZE=512`, `OVERLAP=50`, `TOP_K=8`, `THRESHOLD=0.4` |

After changing any value, run `make restart`. **Changes only affect newly-indexed documents** — existing chunks in Qdrant keep the sizes they were indexed with. Reindex if you want the new sizing everywhere.

---

## Clearing indexed documents

To wipe the Qdrant vector database and start fresh:

```sh
make down
rm -rf data/qdrant
make up
```

The empty collection will be recreated the next time you index a document.

---

## Security notes

DocChat has **no authentication** on any endpoint — it assumes it's running on `localhost` and only you have access to your Mac.

If you plan to expose it beyond localhost (port forwarding to your phone, sharing with a housemate, running on a shared machine), you should add auth first. A simple option is a shared-secret header in front of FastAPI (e.g. a middleware that checks `X-API-Key`).

The `/ui/upload` endpoint caps individual file size at `MAX_UPLOAD_MB` (default 10 MB) to prevent accidental OOMs, but it has no rate limit — someone on your network could still spam it. Fine for local use.

---

## Troubleshooting

**`Cannot connect to Podman` / socket error**
The VM isn't running:

```sh
podman machine start
```

**`404` from `/api/chat` in the UI**
The Ollama model hasn't been pulled yet. Run `make ollama-pull`.

**`make restart` errors about "dependencies not started"**
Known podman-compose quirk. Use:

```sh
make down && make up
```

**Slow first response**
Ollama loads the model into memory on the first request. Subsequent requests are much faster.

**Out of memory / VM sluggish**
Increase VM resources:

```sh
podman machine stop
podman machine set --cpus 6 --memory 12288
podman machine start
```

**Port already in use**
Change `API_PORT`, `OLLAMA_EXTERNAL_PORT`, or `QDRANT_EXTERNAL_PORT` in `.env` and `make restart`.

---

## Project layout

```
api/                 FastAPI application
  app/               Routes, config, clients, models
  templates/         htmx web UI
  tests/             pytest suite
examples/            Standalone scripts (indexing, chat, query)
docker-compose.yml   Service definitions (podman-compatible)
Dockerfile           API container image
Makefile             Common commands
.env.example         Configuration template
```

---

## Uninstall

```sh
make clean
podman machine stop
podman machine rm
brew uninstall podman podman-compose
```
