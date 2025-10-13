# RAG-MCP

A small FastAPI service to upload documents, extract text, call an online embedding model, and store document chunks and embeddings in a local SQLite database.

This repo provides:

- HTTP endpoints for uploading files and triggering vectorization (`/api/v1/upload`, `/api/v1/vectorize`).
- Document parsing for `.docx`, `.pdf`, `.txt`/`.md`.
- An embedding flow using an OpenAI-compatible client (configured by environment variables).

## Requirements

- Python 3.12 (project uses Poetry, see `pyproject.toml`).
- The project depends on packages listed in `pyproject.toml` (FastAPI, uvicorn, python-docx, pypdf2, python-dotenv, openai client, etc.).

## Setup

1. Create and activate a Python environment (recommended: use Poetry):

```bash
poetry install
poetry shell
```

2. Create a `.env` file in the project root (the repository already includes a `.env` file in the workspace). Add the required environment variables (example below).
3. Run the app locally with Uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs to see the interactive API docs.

## Required environment variables

Add these to your `.env` file (example names used in the code):

```env
# OpenAI-compatible client config
OPENAI_API_KEY=sk-xxxx
OPENAI_URL=https://api.openai.com/v1

# Optional: model name to use for embeddings (defaults to Qwen/Qwen3-Embedding-8B)
MODEL_NAME=Qwen/Qwen3-Embedding-8B
```

Depending on your OpenAI-compatible provider you may also need to set different base URL or API key names. The project reads `OPENAI_API_KEY`, `OPENAI_URL`, and `MODEL_NAME` in `api/vectorize.py`.

## Endpoints (high level)

- POST /api/v1/upload — upload a document file. (See `api/upload.py`)
- POST /api/v1/vectorize — accepts a `file_path` (e.g. `upload/your-file.docx`) and will:
  - read and parse the file into text (supports `.docx`, `.pdf`, `.txt`, `.md`),
  - chunk the text into blocks,
  - call the configured embedding model for each chunk,
  - store the document record and chunk embeddings in the database.

Example request to vectorize (from code / API docs):

```json
POST /api/v1/vectorize
{
	"file_path": "upload/b9cbbc03-6608-4b17-95e5-281a5a8f4e83.docx"
}
```

Response sample:

```json
{
  "success": true,
  "message": "文件向量化成功",
  "data": {
    "document_id": 1,
    "filename": "b9cbbc03-6608-4b17-95e5-281a5a8f4e83.docx",
    "file_path": "upload/b9cbbc03-6608-4b17-95e5-281a5a8f4e83.docx",
    "total_chunks": 10,
    "text_length": 12345,
    "file_type": ".docx"
  }
}
```

## Database

The project uses a local SQLite database (see `database/models.py`). On application startup the DB is initialized in `main.py` via the `db_manager.init_database()` call.

## Troubleshooting

- If embeddings fail, check that `OPENAI_API_KEY` and `OPENAI_URL` are correct and reachable from your machine.
- If file parsing fails for certain PDFs, try using a different PDF or check the file is not corrupted.

## Notes & next steps

- Add support for more file types if needed.
- Add batching to embedding calls to improve throughput for large documents.
- Add tests for parsing, chunking and DB persistence.

If you want, I can add example curl commands for upload and vectorize, or add a small test script to call the API — tell me which you prefer.
