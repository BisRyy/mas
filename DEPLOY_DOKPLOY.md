# Deploy on Dokploy

End-to-end runbook for shipping the Inventory MAS stack to a Dokploy
host with HTTPS on your own domain. ~15 minutes start to finish.

## Prerequisites

- Dokploy ≥ 0.18 running on a Linux VM (already done per your setup)
- A private GitHub or GitLab repo (or empty repo ready to receive the push)
- A domain you control, with DNS-edit access
- The Dokploy host's public IP (you'll point DNS at it)

---

## Step 1 — Push the repo

You'll do this from your laptop. (I can't push because I'd need your
credentials; you keep them.)

### 1a. Sanity check what will be committed

From the repo root:

```bash
git status
git diff --stat
```

You should see modifications to `README.md`, `experiments/run.py`,
`requirements.txt`, plus the new `backend/`, `frontend/`,
`docker-compose.yml`, `scripts/`, `DEPLOY_DOKPLOY.md` files.

### 1b. Stage and commit

```bash
git add -A
git status                 # eyeball it — no .env, no .pem, no inventory_mas.db
git commit -m "Deployment-ready: FastAPI backend + Next.js frontend + Docker Compose"
```

### 1c. Create a private repo on GitHub or GitLab

Use the web UI. Don't initialise with README/license — your local repo
already has those. Copy the SSH or HTTPS URL.

### 1d. Add it as a remote and push

```bash
git remote add origin git@github.com:YOUR_USERNAME/inventory-mas.git
git push -u origin main
```

If your default branch is `master` rather than `main`, adapt the command.

---

## Step 2 — Add a deploy key on Dokploy's side

Dokploy needs to clone the private repo without your personal SSH key.

### 2a. Generate a deploy key on the Dokploy host

Open Dokploy → **Settings → SSH Keys → Create**. Name it
`inventory-mas-deploy`. Dokploy generates a key pair and shows you the
**public** half.

### 2b. Authorize it on the repo

In GitHub: **Settings → Deploy keys → Add deploy key**. Paste the
public half. **Do NOT tick "Allow write access"** — read-only is enough.

In GitLab: **Settings → Repository → Deploy keys**.

---

## Step 3 — Create the Dokploy application

Dokploy → **Projects → New Project** (or open an existing one) →
**Add Service → Compose**.

### 3a. Source

- Provider: **Git** (private)
- Repository URL: paste your SSH URL (e.g., `git@github.com:you/inventory-mas.git`)
- Branch: `main`
- SSH Key: select `inventory-mas-deploy`
- Build context: `/`
- Compose file: `docker-compose.yml`

Click **Save**. Don't deploy yet.

### 3b. Environment variables

Open the **Environment** tab. Paste the contents of
`.env.production.example`, replacing the example domains with yours.
For example, if your domain is `mas.example.com`:

```env
APP_DOMAIN=mas.example.com
API_DOMAIN=api-mas.example.com
MAS_CORS_ORIGINS=https://mas.example.com
MAS_ALLOW_RUN_LAUNCH=true
MAS_MAX_QUEUED_RUNS=3
MAS_MAX_CONCURRENT_RUNS=1
MAS_EMIT_DECISIONS=1
NEXT_PUBLIC_API_URL=https://api-mas.example.com
```

`NEXT_PUBLIC_API_URL` matters: it's baked into the Next.js bundle at
build time, so the browser knows where to find the backend.

### 3c. Domains

Open the **Domains** tab and create two entries:

1. **Frontend domain**
   - Host: `mas.example.com` (or whatever you set as `APP_DOMAIN`)
   - Service: `frontend`
   - Container port: `3000`
   - HTTPS: enabled (Dokploy issues a Let's Encrypt cert automatically)

2. **Backend domain**
   - Host: `api-mas.example.com` (or whatever you set as `API_DOMAIN`)
   - Service: `backend`
   - Container port: `8000`
   - HTTPS: enabled

### 3d. Volumes (optional — Dokploy auto-creates from compose)

The compose file declares `results-data` and `db-data` volumes;
Dokploy creates them on first deploy. Nothing to configure manually.

---

## Step 4 — Point DNS

In your domain registrar's DNS panel:

| Type | Name | Value |
|---|---|---|
| A | `mas` | `<dokploy-vm-public-ip>` |
| A | `api-mas` | `<dokploy-vm-public-ip>` |

TTL of 300 is fine. Wait for propagation (`dig mas.example.com +short`
should return the IP — usually instant, occasionally 1–2 min).

---

## Step 5 — Deploy

Back in Dokploy, hit **Deploy**. The first build takes ~5–8 min
(Python deps + statsmodels + Next.js compile). Tail the logs:

- Backend logs should end with `Startup ingest: 0 experiments, 0 seeds, 0 decisions`
  (empty on a fresh deploy — that's expected; we'll seed in Step 6).
- Frontend logs should end with `▲ Next.js 15.x.x — ready in Xs`.

When both services show `healthy`, open `https://mas.example.com`
in your browser. You should see the Overview page (with empty catalog
for now).

---

## Step 6 — Seed historical results (optional but recommended)

The deployment starts empty. To show the dashboard with the existing
296 seeds and 23k+ decision events from your local sweeps, upload the
`results/` directory:

```bash
# From your laptop, in the repo root:
bash scripts/seed_results.sh --host root@<dokploy-vm-ip>
```

The script tars `results/`, scp's it to the VM, extracts into the
backend container's `/app/results`, and hits the `POST /api/experiments/ingest`
endpoint to refresh the SQLite catalog.

After it finishes, refresh the dashboard. The Experiments browser
should now show all 37 experiment cohorts.

---

## Step 7 — Verify

- `https://mas.example.com/` — Overview page renders, hypothesis verdicts
- `https://mas.example.com/experiments` — 37 cohorts listed
- `https://mas.example.com/decisions/olist_mas_no_drift/99` — audit-trail
  viewer (only the seed we ran with `MAS_EMIT_DECISIONS=1`)
- `https://mas.example.com/runs/new` — config dropdown populated; submit
  a small sweep (e.g., `olist_static_rop_no_drift`, seeds `1`)
- `https://api-mas.example.com/api/health` — `{"status":"ok"}`
- `https://api-mas.example.com/docs` — interactive OpenAPI

---

## Updating

When you push new commits to the repo:

- Dokploy → Application → **Deploy** (or set up auto-deploy on push
  in the application's settings)

The volumes persist across redeploys, so your results catalog survives.

---

## Tearing down

- Dokploy → Application → **Delete** (offers an option to keep or
  remove volumes)

---

## Troubleshooting

**Frontend says "Failed to fetch" everywhere.**
The browser is hitting the wrong API URL. Check that the application's
`NEXT_PUBLIC_API_URL` matches `https://<API_DOMAIN>` exactly, then
**rebuild** (not just restart) — the value is baked at build time.

**Backend logs show `ValueError: greenlet library is required`.**
The image didn't install `greenlet`. The `backend/Dockerfile` already
pulls it via `backend/requirements.txt`; clean-rebuild the image.

**WebSocket on /runs/{id} immediately disconnects.**
Most likely Traefik is closing idle connections. Check the application's
**Advanced → Traefik** settings — `passHostHeader: true` and an idle
timeout of 60s+ are fine.

**Sweep launcher returns 429.**
Hit the queue cap. Wait for in-flight jobs to finish or raise
`MAS_MAX_QUEUED_RUNS`.

**Database wiped after redeploy.**
Volumes weren't preserved. Make sure `db-data` shows under
**Volumes** in the Dokploy application UI, not as an anonymous volume.

---

## Cost expectation

On a single `t3.small` / Hetzner CX22 (2 vCPU / 4 GB RAM, ~$5–10/mo):
- Idle (dashboard browsing): well under 200 MB RAM, single-digit %CPU
- During a MAS sweep: ~600 MB RAM, ~100% on one vCPU for the duration
- Disk: ~50 MB for app + 30 MB per 180-run sweep
