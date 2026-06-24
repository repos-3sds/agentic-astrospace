from fastapi import APIRouter, HTTPException
from .models import BirthInfo, CompatibilityRequest, HoroscopeRequest
from ..core.chart import BirthChart
from ..core.transits import TransitCalculator
from ..agents.reading_agent import ReadingAgent
from ..agents.horoscope_agent import HoroscopeAgent
from ..agents.compatibility_agent import CompatibilityAgent
from ..agents.transit_agent import TransitAgent

router = APIRouter(prefix="/api/v1", tags=["AstroSpace"])


@router.post("/chart")
async def get_chart(b: BirthInfo):
    try:
        return {"status": "success", "data": BirthChart(
            b.name, b.year, b.month, b.day, b.hour, b.minute, b.city, b.nation
        ).to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reading")
async def get_reading(b: BirthInfo):
    try:
        return {"status": "success", "reading": ReadingAgent().get_full_reading(
            b.name, b.year, b.month, b.day, b.hour, b.minute, b.city, b.nation
        )}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/horoscope")
async def get_horoscope(req: HoroscopeRequest):
    try:
        agent = HoroscopeAgent()
        result = agent.get_weekly_horoscope(req.sun_sign) if req.weekly else agent.get_daily_horoscope(req.sun_sign)
        return {"status": "success", "horoscope": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compatibility")
async def get_compatibility(req: CompatibilityRequest):
    try:
        p1, p2 = req.person1, req.person2
        return {"status": "success", "compatibility": CompatibilityAgent().get_compatibility_reading(
            p1.name, p1.year, p1.month, p1.day, p1.hour, p1.minute, p1.city, p1.nation,
            p2.name, p2.year, p2.month, p2.day, p2.hour, p2.minute, p2.city, p2.nation,
        )}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transits")
async def get_transits(b: BirthInfo):
    try:
        return {"status": "success", "transits": TransitAgent().get_transit_reading(
            b.name, b.year, b.month, b.day, b.hour, b.minute, b.city, b.nation
        )}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transits/current")
async def current_transits():
    try:
        return {"status": "success", "sky": TransitCalculator().get_current_transits()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
