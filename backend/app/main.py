import html
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select, text

from . import metrics
from .config import get_settings
from .db import SessionLocal, engine, init_db
from .models import Share
from .og import plain_text
from .orchestrator import load_session
from .routes import auth, sessions, share

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
settings = get_settings()

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()


app = FastAPI(title="Decision Court", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    method = request.method
    metrics.http_latency.labels(method=method, path=path).observe(
        time.perf_counter() - start
    )
    metrics.http_requests.labels(
        method=method, path=path, status=str(response.status_code)
    ).inc()
    return response


app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(share.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse({"status": "not-ready"}, status_code=503)


@app.get("/metrics")
async def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _og_tags(title: str, description: str, image: str | None) -> str:
    t, d = html.escape(title), html.escape(description)
    tags = [
        f'<meta property="og:title" content="{t}" />',
        f'<meta property="og:description" content="{d}" />',
        '<meta property="og:type" content="article" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{t}" />',
        f'<meta name="twitter:description" content="{d}" />',
    ]
    if image:
        img = html.escape(image)
        tags += [
            f'<meta property="og:image" content="{img}" />',
            f'<meta name="twitter:image" content="{img}" />',
        ]
    return "\n    ".join(tags)


async def _share_html(token: str) -> str:
    """index.html with verdict-specific Open Graph tags injected, so social/chat
    crawlers (which don't run JS) render a rich preview. Humans still get the SPA."""
    base = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    title, desc, image = "A verdict from Decision Court", "Put your decision on trial.", None
    async with SessionLocal() as db:
        res = await db.execute(select(Share).where(Share.token == token))
        sh = res.scalar_one_or_none()
        if sh:
            session = await load_session(db, sh.session_id)
            if session and session.verdict:
                decision = plain_text((session.intake or {}).get("one_sentence", "")) or "A hard decision"
                title = f"Verdict: {decision}"
                desc = plain_text(session.verdict.recommendation)[:200]
                image = f"{settings.public_base_url}/api/share/{token}/og.png"
    return base.replace("</head>", f"    {_og_tags(title, desc, image)}\n  </head>", 1)


# Serve the built SPA from the same container. SPA fallback for client-side routes.
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/share/{token}", response_class=HTMLResponse)
    async def share_page(token: str):
        return HTMLResponse(await _share_html(token))

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
