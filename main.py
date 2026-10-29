from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from astrospace.logging_config import TraceContextMiddleware, configure_logging

# Before anything else logs: JSON lines at INFO on stdout, which Cloud Logging
# parses. Without it the INFO-level `astrospace.ask.cost` lines were dropped.
configure_logging()

# Warn-only (audit I9): a mistyped flag or number shows in the boot logs
# instead of silently meaning something else. Never stops the server.
from astrospace.config import log_environment_problems  # noqa: E402

log_environment_problems()

from astrospace.db.database import init_db
from astrospace.api.kundli_routes import router as kundli_router
from astrospace.api.reading_routes import router as reading_router
from astrospace.api.vedic_routes import router as vedic_router
from astrospace.api.panchanga_routes import router as panchanga_router
from astrospace.api.ask_routes import router as ask_router
from astrospace.api.ask_stream_routes import router as ask_stream_router
from astrospace.api.auth_routes import router as auth_router
from astrospace.api.context_routes import router as context_router
from astrospace.api.settings_routes import router as settings_router
from astrospace.api.admin_routes import router as admin_router
from astrospace.api.remedy_routes import router as remedy_router
from astrospace.api.muhurta_routes import router as muhurta_router
from astrospace.api.festival_routes import router as festival_router
from astrospace.api.me_routes import router as me_router
from astrospace.api.practice_routes import router as practice_router
from astrospace.api.profile_context_routes import router as profile_context_router
from astrospace.api.entitlement_routes import router as entitlement_router
from astrospace.api.legal_routes import router as legal_router
from astrospace.api.store_routes import router as store_router
from astrospace.api.web_store_routes import router as web_store_router
from astrospace.api.email_routes import router as email_router
from astrospace.api.release_routes import router as release_router
from astrospace.api.app_version_routes import router as app_version_router
from astrospace.api.voice_routes import router as voice_router
from astrospace.api.subhashita_routes import router as subhashita_router
from astrospace.admin.audit_middleware import AppAuditMiddleware
from astrospace.api.auth import running_on_cloud_run
from astrospace.api.security_headers import SecurityHeadersMiddleware
from astrospace.entitlements import EntitlementDenied

_ON_CLOUD_RUN = running_on_cloud_run()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # A lifespan handler; `on_event("startup")` is deprecated (audit I17).
    init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="AstroSpace",
    description="AI-Powered Astrology Engine with Autonomous Agents",
    version="2.0.0",
    # The interactive docs and the schema are a map of every route for
    # anyone who asks. Useful locally; not published from production.
    docs_url=None if _ON_CLOUD_RUN else "/docs",
    redoc_url=None if _ON_CLOUD_RUN else "/redoc",
    openapi_url=None if _ON_CLOUD_RUN else "/openapi.json",
)

# The web SPA is served same-origin, so CORS only matters for local dev
# (ng serve on :4200) and for the native apps.
#
# A Capacitor WebView is a genuine cross-origin caller: it serves the bundle
# from https://localhost, so every API request is cross-origin and is blocked
# without these entries. The failure only appears on device, which is an
# expensive place to discover a CORS list.
#
# They are therefore always present and are NOT part of the configurable set.
# ALLOWED_ORIGINS replaces the dev defaults, so folding these in with them
# meant that pointing it at a production domain silently broke every native
# build — and the app's own fallback made that look like a config problem
# rather than a CORS one.
_NATIVE_ORIGINS = (
    "https://localhost",       # Capacitor iOS and Android
    "capacitor://localhost",   # older Capacitor iOS scheme
)

_DEV_ORIGINS = (
    "http://localhost:4200",   # ng serve
    "http://localhost:8000",   # local FastAPI
)

_configured = os.getenv("ALLOWED_ORIGINS")
# The dev defaults are a fallback for a developer's machine only. On Cloud Run
# with ALLOWED_ORIGINS unset they used to apply too, which allowed any page
# served from localhost to make credentialed calls to production. The web SPA
# is same-origin there and needs no entry.
_fallback = () if _ON_CLOUD_RUN else _DEV_ORIGINS
_origins = [
    origin.strip()
    for origin in (_configured.split(",") if _configured else _fallback)
    if origin.strip()
]
# dict.fromkeys rather than set(): order is stable, which keeps the resolved
# list readable in logs and in tests.
_origins = list(dict.fromkeys([*_origins, *_NATIVE_ORIGINS]))

app.add_middleware(AppAuditMiddleware)
# Compresses the fully-formed response after the audit log has run, and after
# Starlette has served the static SPA bundle.
# Nothing was compressed before this: neither the ~150 KB /vedic/{id}/all
# JSON nor the ~340 KB main JS chunk, both served uncompressed to phones.
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware, on_cloud_run=_ON_CLOUD_RUN)
# Added last, so it is the outermost layer: every line logged while handling
# a request, the audit middleware's included, carries the Cloud Trace id.
app.add_middleware(TraceContextMiddleware)


@app.exception_handler(EntitlementDenied)
async def entitlement_denied_handler(_request, exc: EntitlementDenied):
    return JSONResponse(status_code=402, content=exc.decision.denial())

# API routers
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(kundli_router)
app.include_router(reading_router)
app.include_router(vedic_router)
app.include_router(panchanga_router)
app.include_router(ask_router)
app.include_router(ask_stream_router)
app.include_router(context_router)
app.include_router(admin_router)
app.include_router(remedy_router)
app.include_router(muhurta_router)
app.include_router(festival_router)
app.include_router(me_router)
app.include_router(practice_router)
app.include_router(profile_context_router)
app.include_router(entitlement_router)
app.include_router(voice_router)
app.include_router(subhashita_router)
# Terms + Privacy Policy pages; must precede the SPA mount like /api/health.
app.include_router(legal_router)
app.include_router(store_router)
app.include_router(web_store_router)
app.include_router(email_router)
app.include_router(release_router)
app.include_router(app_version_router)

# Registered before the "/" SPA mount — Starlette matches in registration
# order, so anything defined after the mount is unreachable.
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version}


# Serve the built Angular SPA (ui/ workspace builds into frontend/dist/browser)
DIST = Path(__file__).parent / "frontend" / "dist" / "browser"


def _is_api_path(path: str) -> bool:
    # `path` is relative to the mount, without the leading slash.
    return path == "api" or path.startswith("api/")


class SPAStaticFiles(StaticFiles):
    """Static files with SPA fallback: unknown paths serve index.html so
    client-side routes like /kundli/:id survive a full page load.

    Never for /api/*: an unknown API path used to come back as 200 with the
    SPA's index.html, which a client then failed to parse as JSON and a
    scanner read as "exists". It gets FastAPI's own JSON 404 instead."""

    async def get_response(self, path, scope):
        from fastapi import HTTPException
        from starlette.exceptions import HTTPException as StarletteHTTPException

        if _is_api_path(path):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        try:
            response = await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404:
            response = await super().get_response("index.html", scope)
        return response


if DIST.exists():
    app.mount("/", SPAStaticFiles(directory=str(DIST), html=True), name="spa")
else:
    @app.get("/")
    async def root():
        return {
            "engine": "AstroSpace",
            "version": "2.0.0",
            "docs": "/docs",
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port,
                reload=os.getenv("PORT") is None)
