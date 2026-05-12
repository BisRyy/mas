# Deployment

The Tier-3 observability stack ships as **two containers** orchestrated by
Docker Compose:

| Service | What it does | Port |
|---|---|---|
| `backend` | FastAPI + simulator. Serves `/api/*`, runs sweeps in-process, ingests `results/` into SQLite, streams progress via WebSocket. | 8000 |
| `frontend` | Next.js 15 dashboard (App Router, TypeScript). Renders all UI: Overview, Experiments browser, Detail, Compare, Decision-log audit, Reports, Run launcher with live progress. | 3000 |

## Local development

```bash
# 1. Backend
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# 2. Frontend (in another terminal)
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

The frontend's `next.config.ts` proxies `/api/*` to `http://localhost:8000`
in dev so you don't have to deal with CORS.

## Docker Compose (single-host deployment)

```bash
docker compose up -d --build
docker compose logs -f
# open http://<host>:3000
```

This works as-is on:

- **Local docker** (Mac, Linux)
- **Dokploy** — point its "Deploy from compose file" at this repo
- **AWS EC2 / Lightsail / Azure VM** — `git clone`, then `docker compose up -d`

The backend persists state in two named volumes:

- `results-data` — every sweep's `summary.json`, `timeseries.csv`,
  and (if `MAS_EMIT_DECISIONS=1`) `decisions.jsonl`
- `db-data` — SQLite catalog of experiments, seeds, decisions, jobs

To wipe state, `docker compose down -v`.

### Environment variables

| Var | Default | Purpose |
|---|---|---|
| `MAS_ALLOW_RUN_LAUNCH` | `true` | Set `false` for read-only public demos |
| `MAS_MAX_QUEUED_RUNS` | `3` | Cap on simultaneously queued sweeps |
| `MAS_MAX_CONCURRENT_RUNS` | `1` | Cap on in-flight sweep workers (each is CPU-heavy) |
| `MAS_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed frontend origins. Update to your public domain in production. |
| `MAS_EMIT_DECISIONS` | `1` | When set, each sweep writes `decisions.jsonl` for the audit-trail viewer. Disable to save disk on light deployments. |
| `NEXT_PUBLIC_API_URL` (frontend) | `http://backend:8000` | Where the frontend rewrites `/api/*`. In production set to the public backend URL. |

## Production checklist

When deploying behind a real domain:

1. **Reverse proxy** (Traefik / Caddy / nginx) terminates TLS, routes:
   - `/api/*` → `backend:8000`
   - everything else → `frontend:3000`
2. Set `MAS_CORS_ORIGINS=https://yourdomain.example` on the backend
3. Set `NEXT_PUBLIC_API_URL=https://yourdomain.example` on the frontend at
   build time (or via `docker compose build --build-arg`)
4. Consider `MAS_ALLOW_RUN_LAUNCH=false` if you don't want public visitors
   to trigger sweeps on your VM
5. Mount the `results-data` volume on a path with enough disk (one
   180-run sweep produces ~30 MB of JSON + CSV)

## Updating

```bash
git pull
docker compose up -d --build       # rebuilds images, keeps volumes
```

## Tearing down

```bash
docker compose down        # stop containers, keep volumes
docker compose down -v     # also wipe results + db
```

## Architecture diagram

```
Browser
   │ HTTPS
   ▼
[Reverse proxy]   (Caddy/Traefik/nginx — provide your own)
   │   /api/*        /
   ▼                 ▼
backend:8000     frontend:3000
   │                 │
   │   reads/writes  │   server-side fetches /api/*
   ▼                 │
results-data        (Next.js standalone bundle)
SQLite db-data
```

## Endpoints reference

- `GET  /api/health`
- `GET  /api/experiments[?family=&policy=&scenario=]`
- `GET  /api/experiments/{name}`
- `POST /api/experiments/ingest` — re-walk `results/` and refresh DB
- `GET  /api/experiments/_stats/families`
- `GET  /api/experiments/{name}/seeds`
- `GET  /api/experiments/{name}/seeds/{seed_num}`
- `GET  /api/experiments/{name}/seeds/{seed_num}/timeseries`
- `GET  /api/experiments/{name}/seeds/{seed_num}/decisions[?agent=&action=&sku=&step_min=&step_max=&page=&page_size=]`
- `GET  /api/experiments/{name}/seeds/{seed_num}/decisions/skus`
- `GET  /api/experiments/{name}/seeds/{seed_num}/decisions/agents`
- `GET  /api/reports/h1`
- `GET  /api/reports/h3`
- `GET  /api/reports/ablation`
- `GET  /api/configs`
- `GET  /api/configs/{name}`
- `POST /api/runs`
- `GET  /api/runs[?status=]`
- `GET  /api/runs/{job_id}`
- `WS   /api/runs/{job_id}/stream`

Interactive OpenAPI docs at `http://<host>:8000/docs`.
