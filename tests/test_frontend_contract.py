"""The server's responses carry every field the app's TypeScript types promise
(audit I12: front-end/back-end contract).

ui/src/app/core/models.ts is what the app's screens are written against. A
key the server drops or renames compiles cleanly on both sides and shows up
as a blank card on a phone. This reads the interfaces straight from
models.ts and checks real responses from the routes below against them:
every key not marked optional must be present (null is accepted where the
type allows it). Extra keys from the server are fine.

The parser understands the subset models.ts uses for these payloads:
nested object literals, named interfaces, `A & { ... }`, `T[]` and
`Array<T>`, and `?` for optional keys. Anything else (unions of string
literals, Record<...>, primitives) is checked for presence only.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from main import app

MODELS_TS = Path(__file__).resolve().parents[1] / "ui" / "src" / "app" / "core" / "models.ts"
ME = "contract-reader"


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def _matching(src: str, start: int) -> int:
    """Index of the brace closing the one at `start`."""
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced braces in models.ts")


def _interfaces(src: str) -> dict[str, str]:
    found = {}
    for match in re.finditer(r"export interface (\w+)(?:\s+extends\s+([\w,\s]+))?\s*\{", src):
        body_start = match.end() - 1
        body = src[body_start + 1:_matching(src, body_start)]
        if match.group(2):
            body = " ".join(f"...{name.strip()};" for name in match.group(2).split(",")) + body
        found[match.group(1)] = body
    for match in re.finditer(r"export type (\w+)\s*=\s*([^;]+);", src):
        found.setdefault(match.group(1), "=" + match.group(2).strip())
    return found


def _members(body: str) -> list[tuple[str, bool, str]]:
    """(key, optional, type) for each member at this level of an object body."""
    members, i = [], 0
    body = body.strip()
    while i < len(body):
        while i < len(body) and body[i] in " \n\t;,":
            i += 1
        if i >= len(body):
            break
        if body.startswith("...", i):
            end = body.index(";", i)
            members.append(("...", False, body[i + 3:end].strip()))
            i = end + 1
            continue
        match = re.match(r"(readonly\s+)?['\"]?([\w-]+)['\"]?(\?)?\s*:\s*", body[i:])
        if not match:  # an index signature or something this parser skips
            end = body.find(";", i)
            i = len(body) if end == -1 else end + 1
            continue
        i += match.end()
        start, depth = i, 0
        while i < len(body):
            ch = body[i]
            if ch in "{(<[":
                depth += 1
            elif ch in "})>]":
                depth -= 1
            elif ch in ";," and depth == 0:
                break
            elif ch == "\n" and depth == 0 and not body[start:i].rstrip().endswith(("|", "&")) \
                    and not body[i:].lstrip().startswith(("|", "&")):
                break
            i += 1
        members.append((match.group(2), bool(match.group(3)), body[start:i].strip()))
    return members


class Contract:
    def __init__(self) -> None:
        self.types = _interfaces(_strip_comments(MODELS_TS.read_text()))

    def check(self, value, type_src: str, path: str, problems: list[str], depth: int = 0) -> None:
        if depth > 8 or value is None:
            return
        type_src = type_src.strip()
        if type_src.startswith("(") and type_src.endswith(")"):
            type_src = type_src[1:-1].strip()
        if "|" in _top_level(type_src, "|"):
            return  # a union: presence was all we could check
        parts = _top_level(type_src, "&")
        if len(parts) > 1:
            for part in parts:
                self.check(value, part, path, problems, depth + 1)
            return
        array = re.fullmatch(r"(.+)\[\]", type_src, re.S) or re.fullmatch(r"Array<(.+)>", type_src, re.S)
        if array:
            if isinstance(value, list):
                for index, item in enumerate(value[:3]):
                    self.check(item, array.group(1), f"{path}[{index}]", problems, depth + 1)
            return
        if type_src.startswith("{"):
            self._object(value, type_src[1:_matching(type_src, 0)], path, problems, depth)
            return
        body = self.types.get(type_src)
        if body is None:
            return
        if body.startswith("="):
            self.check(value, body[1:], path, problems, depth + 1)
        else:
            self._object(value, body, path, problems, depth)

    def _object(self, value, body: str, path: str, problems: list[str], depth: int) -> None:
        if not isinstance(value, dict):
            problems.append(f"{path} should be an object")
            return
        for key, optional, type_src in _members(body):
            if key == "...":
                self.check(value, type_src, path, problems, depth + 1)
                continue
            if key not in value:
                if not optional:
                    problems.append(f"{path}.{key} is missing")
                continue
            self.check(value[key], type_src, f"{path}.{key}", problems, depth + 1)


def _top_level(src: str, sep: str) -> list[str]:
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(src):
        if ch in "{(<[":
            depth += 1
        elif ch in "})>]":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(src[start:i])
            start = i + 1
    parts.append(src[start:])
    return [part.strip() for part in parts if part.strip()]


@pytest.fixture(scope="module")
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    with factory() as db:
        kundli = crud.create_kundli(db, {
            "user_id": ME, "name": "Reader", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, role="dev")
    try:
        yield TestClient(app), kundli
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


ROUTES = [
    ("/api/v1/kundlis", "Kundli[]"),
    ("/api/v1/context/{id}/daily?timezone=Asia/Kolkata", "DailyGuidancePayload"),
    ("/api/v1/vedic/{id}/all", "VedicAll"),
    ("/api/v1/festivals/upcoming?city=Hyderabad&nation=IN&from_date=2026-10-01&days=31",
     "FestivalWindowPayload"),
    ("/api/v1/panchanga/{id}/today?timezone=Asia/Kolkata", "PanchangaDay"),
    ("/api/v1/panchanga/{id}/month?from_date=2026-10-01&days=31&timezone=Asia/Kolkata",
     "MonthQualityPayload"),
    ("/api/v1/vedic/{id}/calendar-intelligence?days=7&timezone=Asia/Kolkata",
     "CalendarIntelligencePayload"),
    ("/api/v1/festivals/vrat-days?city=Hyderabad&nation=IN&from_date=2026-10-01&days=31",
     "VratDaysPayload"),
]


@pytest.mark.parametrize("route,type_name", ROUTES)
def test_response_matches_the_app_type(client, route, type_name):
    test_client, kundli = client
    contract = Contract()
    assert type_name.rstrip("[]") in contract.types, f"{type_name} is not in models.ts"
    response = test_client.get(route.replace("{id}", kundli))
    assert response.status_code == 200, response.text[:300]
    problems: list[str] = []
    contract.check(response.json(), type_name, type_name, problems)
    assert problems == []


def test_the_checker_notices_a_missing_key():
    contract = Contract()
    problems: list[str] = []
    contract.check({"id": "k"}, "Kundli", "Kundli", problems)
    assert any(problem.endswith(".name is missing") for problem in problems)
