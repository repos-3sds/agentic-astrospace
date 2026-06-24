from pydantic import BaseModel
from typing import Optional


class BirthInfo(BaseModel):
    name: str
    year: int
    month: int
    day: int
    hour: int = 12
    minute: int = 0
    city: str
    nation: str = "US"


class CompatibilityRequest(BaseModel):
    person1: BirthInfo
    person2: BirthInfo


class HoroscopeRequest(BaseModel):
    sun_sign: str
    weekly: bool = False
