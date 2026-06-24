import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from astrospace.api.routes import router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AstroSpace",
    description="AI-Powered Astrology Engine with Autonomous Agents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "engine": "AstroSpace",
        "version": "1.0.0",
        "description": "AI-Powered Astrology Engine",
        "endpoints": {
            "chart": "/api/v1/chart",
            "reading": "/api/v1/reading",
            "horoscope": "/api/v1/horoscope",
            "compatibility": "/api/v1/compatibility",
            "transits": "/api/v1/transits",
            "current_transits": "/api/v1/transits/current",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
