# Docker Compose vs local dev — command reference

All **Docker Compose** commands assume the **repository root** as the current directory:

`docker compose -f docker/docker-compose.yml …`

When developing **without Docker**, use the commands in the third column. For Chroma, `backend/.env` should use `CHROMADB_HOST=localhost` and `CHROMADB_PORT=8001` (see `backend/.env.example`) so the API matches a Chroma server on **host port 8001**.

## Service mapping

| Before (three terminals) | In Compose | Without Docker (explicit commands) |
|--------------------------|------------|-------------------------------------|
| Terminal: Chroma | `chromadb` service | `cd backend && poetry run chroma run --host localhost --port 8001`<br><br>If you use another port, set `CHROMADB_PORT` in `backend/.env`. |
| Terminal: `uvicorn` | `backend` service (`--reload` on) | `cd backend && poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload` |
| Terminal: `npm run dev` | `frontend` service (Node image, not the production nginx Dockerfile) | `cd frontend && npm run dev` |

## Compose networking note

While the stack runs in Compose, `docker-compose.yml` sets `CHROMADB_HOST=chromadb` and `CHROMADB_PORT=8000` so the backend reaches Chroma **over the Docker network** (service name + Chroma’s internal port). Those values **override** `localhost` / `8001` from `backend/.env`.

## URLs (either workflow)

| Service | URL |
|---------|-----|
| Frontend (Vite) | http://localhost:3000 |
| API (FastAPI) | http://localhost:8000/docs |
| Chroma (host, optional) | http://localhost:8001 |

## Related

Full Compose usage (run, rebuild, detached mode): [`docker/README.md`](README.md).
