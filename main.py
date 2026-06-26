import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from astrospace.db.database import init_db
from astrospace.api.routes import router as core_router
from astrospace.api.kundli_routes import router as kundli_router
from astrospace.api.reading_routes import router as reading_router

app = FastAPI(
    title="AstroSpace",
    description="AI-Powered Astrology Engine with Autonomous Agents",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(core_router)
app.include_router(kundli_router)
app.include_router(reading_router)

# Serve frontend static files
FRONTEND = Path(__file__).parent / "frontend"
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

    @app.get("/", response_class=FileResponse)
    async def serve_ui():
        return str(FRONTEND / "index.html")

    @app.get("/app", response_class=FileResponse)
    async def serve_app():
        return str(FRONTEND / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "engine": "AstroSpace",
            "version": "2.0.0",
            "docs": "/docs",
        }


@app.on_event("startup")
def on_startup():
    init_db()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
