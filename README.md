# Decision Court

> Put your decision on trial.

Bring a hard personal decision. Three AI agents — a **Prosecutor**, a **Defender**, and a
**Judge** — argue it out, cross-examine you, and hand down a written **verdict with a dissent**
you can keep, download, or share.

- **Backend:** FastAPI + Groq (streaming chat completions) → Server-Sent Events
- **Frontend:** React + Vite (TypeScript), built to static assets, served by the same container
- **DB:** PostgreSQL (sessions, transcripts, verdicts, share tokens)
- **Deploy:** single image `jaysuzi5/decision-court` → homelab k8s, exposed via Cloudflare tunnel

The three agent personalities live in version-controlled prompt files under [`prompts/`](prompts/)
so they're easy to iterate.

---

## Local development

One command (Docker) — needs only a Groq API key:

```bash
cp .env.example .env          # put your GROQ_API_KEY in it
echo "GROQ_API_KEY=gsk_..." >> .env
docker compose up --build
# open http://localhost:8000
```

Set `DEV_MODE=true` in `.env` to force the cheap/instant model (`llama-3.1-8b-instant`) on
every turn while iterating.

### Running backend + frontend separately (hot reload)

```bash
# Postgres
docker compose up db -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY=gsk_...
export DATABASE_URL=postgresql+asyncpg://decisioncourt:decisioncourt@localhost:5432/decisioncourt
uvicorn app.main:app --reload

# Frontend (proxies /api to :8000)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

---

## Models

Configurable via env / ConfigMap (verify IDs against <https://console.groq.com/docs>):

| Purpose | Env | Default |
|---|---|---|
| Debate turns + Judge questions | `MODEL_DEBATE` | `llama-3.3-70b-versatile` |
| Verdict synthesis | `MODEL_VERDICT` | `openai/gpt-oss-120b` |
| Dev / cost-test (when `DEV_MODE=true`) | `MODEL_DEV` | `llama-3.1-8b-instant` |

Cost guardrails: `MAX_TOKENS_PER_TURN`, `MAX_TOKENS_PER_SESSION`, `MAX_JUDGE_QUESTIONS`.
When a session nears its token cap it is gracefully fast-forwarded to the verdict.

---

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/session` | Create a session from intake (runs the crisis pre-check) |
| GET | `/api/session/{id}/stream` | SSE stream of agent turns |
| POST | `/api/session/{id}/reply` | Answer the Judge; advances the proceeding |
| GET | `/api/session/{id}` | Full transcript + verdict (reload/resume) |
| GET | `/api/session/{id}/markdown` | Download transcript as Markdown |
| DELETE | `/api/session/{id}` | Hard-delete a session |
| POST | `/api/session/{id}/share` | Mint a read-only share token (verdict-only by default) |
| GET | `/api/share/{token}` | Public read-only view |
| GET | `/healthz` `/readyz` | Liveness / readiness |

The orchestrator persists after every turn, so a dropped SSE connection just reconnects and
resumes — `status` advances only once a turn is saved.

---

## Build & push the image

```bash
docker build -t jaysuzi5/decision-court:$(git rev-parse --short HEAD) -t jaysuzi5/decision-court:latest .
docker push jaysuzi5/decision-court:latest
```

---

## Deploy to the homelab (ArgoCD)

Manifests are raw YAML under [`k8s/`](k8s/) (matching the `todo` / `vacation-planner` repos):
namespace, a dedicated Postgres StatefulSet (NFS-backed `nfs-client` storage), the app
Deployment (resource requests **and** limits, `/healthz` + `/readyz` probes, non-root),
a `LoadBalancer` Service, ConfigMap, and a SealedSecret.

### 1. Seal the secrets (never commit plaintext)

```bash
export GROQ_API_KEY=gsk_...           # the Decision Court project key
export POSTGRES_PASSWORD='<choose-a-strong-one>'
./k8s/seal-secrets.sh                  # writes k8s/sealedsecret.yaml (ciphertext only)
```

> If `GROQ_API_KEY` ever lands in a committed file, treat it as compromised and rotate it
> in the Groq console immediately.

### 2. Register the ArgoCD Application

```bash
kubectl apply -f argocd/application.yaml
```

ArgoCD syncs `k8s/` into the `decision-court` namespace (auto-prune + self-heal), the same
pattern as the other apps. Or `kubectl apply -f k8s/` directly to bootstrap once.

### 3. Expose via Cloudflare tunnel

Like `todo.jaycurtis.org` / `vacations.jaycurtis.org`: add a hostname to your existing
`cloudflared` tunnel config mapping `decision-court.jaycurtis.org` → the in-cluster service
`http://decision-court.decision-court.svc.cluster.local:80` (or the Service's LB IP). No
public TLS to manage in-cluster — Cloudflare terminates it. Internal-only access also works
via the `LoadBalancer` IP (metallb).

---

## Safety

A structural crisis pre-check ([`backend/app/safety.py`](backend/app/safety.py)) runs on the
intake and on every reply **before** any trial turn. On a detected signal the proceeding stops,
the courtroom framing is dropped, and region-appropriate resources are shown (default `US`:
988 + Crisis Text Line — set `CRISIS_REGION`). The agents are also instructed via a shared
house-rules preamble to never demean the person, never claim professional credentials, and to
break character for safety. Intake is private: the default share link exposes only the verdict
and dissent, never the raw intake.

---

## Out of scope (MVP)

User accounts/auth, long-term memory across decisions, voice input, payments, multi-language,
analytics dashboards. The schema leaves room to add auth later.
