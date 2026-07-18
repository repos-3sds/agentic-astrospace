import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from astrospace.db.database import init_db
from astrospace.api.routes import router as core_router
from astrospace.api.kundli_routes import router as kundli_router
from astrospace.api.reading_routes import router as reading_router
from astrospace.api.vedic_routes import router as vedic_router
from astrospace.api.panchanga_routes import router as panchanga_router
from astrospace.api.ask_routes import router as ask_router
from astrospace.api.auth_routes import router as auth_router
from astrospace.api.context_routes import router as context_router
from astrospace.api.settings_routes import router as settings_router

app = FastAPI(
    title="AstroSpace",
    description="AI-Powered Astrology Engine with Autonomous Agents",
    version="2.0.0",
)

# In production the SPA is served same-origin, so CORS only matters for local
# dev (ng serve on :4200) and any extra origins listed in ALLOWED_ORIGINS.
_default_origins = "http://localhost:4200,http://localhost:8000"
_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(core_router)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(kundli_router)
app.include_router(reading_router)
app.include_router(vedic_router)
app.include_router(panchanga_router)
app.include_router(ask_router)
app.include_router(context_router)

# Serve the built Angular SPA (ui/ workspace builds into frontend/dist/browser)
DIST = Path(__file__).parent / "frontend" / "dist" / "browser"


class SPAStaticFiles(StaticFiles):
    """Static files with SPA fallback: unknown paths serve index.html so
    client-side routes like /kundli/:id survive a full page load."""

    async def get_response(self, path, scope):
        from fastapi import HTTPException
        from starlette.exceptions import HTTPException as StarletteHTTPException

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.on_event("startup")
def on_startup():
    init_db()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port,
                reload=os.getenv("PORT") is None)
