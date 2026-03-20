# Run the project locally

Commands to run **Sounds Good** on your machine: backend (FastAPI), frontend (Vite), and ChromaDB when you use library sync / vector search.

## Prerequisites

- **Python 3.11+** and [Poetry](https://python-poetry.org/)
- **Node.js** (current LTS) and npm
- **Docker** (optional but recommended for ChromaDB)

## One-time setup

From the repository root:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and `frontend/.env` with real values (Spotify app credentials, `SECRET_KEY`, `ENCRYPTION_KEY`, `GROQ_API_KEY`, etc.).

Install dependencies:

```bash
cd backend && poetry install && cd ..
cd frontend && npm install && cd ..
```

Apply database migrations (when models change):

```bash
cd backend && poetry run alembic upgrade head && cd ..
```

## Processes to run

You usually need **three** things: ChromaDB (for sync/search), the API, and the UI. SQLite does not require a separate server.

### 1. ChromaDB (library sync & embeddings)

The backend expects Chroma at **`localhost:8001`** by default (`CHROMADB_HOST` / `CHROMADB_PORT` in `backend/.env`).

**Option A — Docker Compose (only the Chroma service):**

```bash
docker compose -f docker/docker-compose.yml up chromadb -d
```

**Option B — Standalone container (same host port):**

```bash
docker run -d --name sounds-good-chroma -p 8001:8000 chromadb/chroma:latest
```

Skip this only if you are not hitting endpoints that use embeddings / Chroma (e.g. auth-only flows).

### 2. Backend (FastAPI)

```bash
cd backend
poetry run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 3. Frontend (Vite)

In another terminal:

```bash
cd frontend
npm run dev
```

- App: [http://localhost:3000](http://localhost:3000) (port is set in `frontend/vite.config.ts`)

## Optional: full stack in Docker

To run backend + frontend + ChromaDB together via Compose (see `docker/docker-compose.yml`):

```bash
docker compose -f docker/docker-compose.yml up --build
```

Adjust env/volumes as needed for your setup; Compose wires `CHROMADB_HOST=chromadb` for the backend container.

## What you can skip

| Piece | When |
|--------|------|
| **Redis** | Not used by application code yet; `REDIS_URL` is reserved for future use. |
| **ChromaDB** | Only required for features that index or query vectors (e.g. library sync with embeddings). |

## External services (no local process)

Spotify Web API (OAuth + library), and Groq when you call LLM-related features, are reached over the network using keys from `.env`.
