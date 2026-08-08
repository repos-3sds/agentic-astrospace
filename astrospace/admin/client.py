from __future__ import annotations

import os
import re
from typing import Any

import requests
from psycopg.types.json import Json


class AdminStorageError(RuntimeError):
    pass


class SupabaseAdminClient:
    def __init__(self, url: str | None = None, secret: str | None = None):
        self.url = (url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.secret = (
            secret
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SECRET_KEY")
            or ""
        )
        self.database_url = os.getenv("DATABASE_URL") or ""
        if not self.url:
            raise AdminStorageError(
                "Knowledge Console requires SUPABASE_URL"
            )
        if not self.secret and not self._db_available():
            raise AdminStorageError(
                "Knowledge Console requires a backend Supabase secret or DATABASE_URL"
            )
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.secret,
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    def _db_available(self) -> bool:
        return self.database_url.startswith(("postgres://", "postgresql://", "postgresql+"))

    def _db_url(self) -> str:
        return self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def _db_session(self):
        try:
            from astrospace.db.database import SessionLocal
        except Exception as exc:
            raise AdminStorageError(str(exc)) from exc
        return SessionLocal()

    def _db_fetchall(self, sql: str, values: list[Any] | tuple[Any, ...] = ()) -> list[dict]:
        try:
            with self._db_session() as session:
                result = session.connection().exec_driver_sql(sql, tuple(values))
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as exc:
            raise AdminStorageError(str(exc)) from exc

    def _db_write_returning(self, sql: str, values: list[Any] | tuple[Any, ...] = ()) -> list[dict]:
        try:
            with self._db_session() as session:
                result = session.connection().exec_driver_sql(sql, tuple(values))
                rows = [dict(row._mapping) for row in result.fetchall()]
                session.commit()
                return rows
        except Exception as exc:
            raise AdminStorageError(str(exc)) from exc

    def _adapt(self, value: Any) -> Any:
        return Json(value) if isinstance(value, (dict, list)) else value

    def _identifier(self, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise AdminStorageError(f"Unsupported database identifier: {value}")
        return f'"{value}"'

    def _select_sql(self, table: str, select: str | None) -> str:
        if not select or select == "*":
            return "*"
        columns = []
        for raw in select.split(","):
            column = raw.strip()
            if not column or "(" in column or ")" in column:
                return "*"
            columns.append(self._identifier(column))
        return ", ".join(columns) if columns else "*"

    def _where_sql(self, params: dict[str, Any]) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        for key, value in params.items():
            if key in {"select", "order", "limit", "offset", "on_conflict", "or"}:
                continue
            column = self._identifier(key)
            text = str(value)
            if text.startswith("eq."):
                clauses.append(f"{column} = %s")
                raw = text[3:]
                values.append(True if raw == "true" else False if raw == "false" else raw)
            elif text.startswith("in.(") and text.endswith(")"):
                raw_values = [
                    item.strip()
                    for item in text[4:-1].split(",")
                    if item.strip()
                ]
                if not raw_values:
                    clauses.append("false")
                else:
                    placeholders = ", ".join(["%s"] * len(raw_values))
                    clauses.append(f"{column} in ({placeholders})")
                    values.extend(raw_values)
            elif text.startswith("ilike.*") and text.endswith("*"):
                clauses.append(f"{column} ilike %s")
                values.append(f"%{text[7:-1]}%")
            else:
                raise AdminStorageError(f"Unsupported admin filter: {key}={text}")
        or_filter = params.get("or")
        if isinstance(or_filter, str) and or_filter.startswith("(") and or_filter.endswith(")"):
            or_clauses = []
            for part in or_filter[1:-1].split(","):
                bits = part.split(".")
                if len(bits) >= 3 and bits[1] == "ilike":
                    or_clauses.append(f"{self._identifier(bits[0])} ilike %s")
                    values.append("%" + ".".join(bits[2:]).strip("*") + "%")
            if or_clauses:
                clauses.append("(" + " or ".join(or_clauses) + ")")
        return (" where " + " and ".join(clauses)) if clauses else "", values

    def _db_rows(self, table: str, *, params: dict | None = None) -> list[dict]:
        query = dict(params or {})
        select_sql = self._select_sql(table, query.get("select"))
        where_sql, values = self._where_sql(query)
        sql = f"select {select_sql} from public.{self._identifier(table)}{where_sql}"
        order = query.get("order")
        if order:
            order_column, _, direction = str(order).partition(".")
            sql += f" order by {self._identifier(order_column)} {'desc' if direction == 'desc' else 'asc'}"
        if "limit" in query:
            sql += " limit %s"
            values.append(int(query["limit"]))
        if "offset" in query:
            sql += " offset %s"
            values.append(int(query["offset"]))
        return self._db_fetchall(sql, values)

    def _db_insert(self, table: str, payload: dict | list[dict]) -> list[dict]:
        rows = payload if isinstance(payload, list) else [payload]
        if not rows:
            return []
        columns = list(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        sql = (
            f"insert into public.{self._identifier(table)} "
            f"({', '.join(self._identifier(c) for c in columns)}) values ({placeholders}) "
            "returning *"
        )
        out = []
        for row in rows:
            values = [self._adapt(row.get(c)) for c in columns]
            out.extend(self._db_write_returning(sql, values))
        return out

    def _db_patch(self, table: str, *, params: dict, payload: dict) -> list[dict]:
        where_sql, values = self._where_sql(params)
        if not where_sql:
            raise AdminStorageError("Refusing admin patch without a filter")
        assignments = ", ".join(f"{self._identifier(key)} = %s" for key in payload)
        sql = f"update public.{self._identifier(table)} set {assignments}{where_sql} returning *"
        adapted = [self._adapt(v) for v in payload.values()]
        return self._db_write_returning(sql, [*adapted, *values])

    def request(self, method: str, path: str, *, params: dict | None = None,
                json: Any = None, prefer: str | None = None) -> requests.Response:
        if not self.secret:
            if method == "POST" and path == "admin_users":
                return _JsonResponse(self._db_upsert_admin_user(json))
            raise AdminStorageError("This admin operation requires SUPABASE_SERVICE_ROLE_KEY")
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = requests.request(
                method,
                f"{self.rest_url}/{path}",
                headers=headers,
                params=params,
                json=json,
                timeout=45,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                detail = exc.response.text[:500]
            raise AdminStorageError(detail or str(exc)) from exc

    def rows(self, table: str, *, params: dict | None = None) -> list[dict]:
        if not self.secret:
            return self._db_rows(table, params=params)
        query = dict(params or {})
        if "limit" in query:
            return self.request("GET", table, params=query).json()
        page_size = 1000
        offset = int(query.pop("offset", 0))
        rows = []
        while True:
            page = self.request(
                "GET",
                table,
                params={**query, "limit": page_size, "offset": offset},
            ).json()
            rows.extend(page)
            if len(page) < page_size:
                return rows
            offset += page_size

    def one(self, table: str, *, params: dict) -> dict | None:
        rows = self.rows(table, params={**params, "limit": 1})
        return rows[0] if rows else None

    def insert(self, table: str, payload: dict | list[dict]) -> list[dict]:
        if not self.secret:
            return self._db_insert(table, payload)
        return self.request(
            "POST", table, json=payload, prefer="return=representation",
        ).json()

    def patch(self, table: str, *, params: dict, payload: dict) -> list[dict]:
        if not self.secret:
            return self._db_patch(table, params=params, payload=payload)
        return self.request(
            "PATCH", table, params=params, json=payload,
            prefer="return=representation",
        ).json()

    def audit(self, *, actor, action: str, entity_type: str,
              entity_id: str | None = None, source_id: str | None = None,
              reason: str | None = None, before: dict | None = None,
              after: dict | None = None, request_id: str | None = None):
        payload = {
            "actor_id": actor.id if actor.auth_enabled else None,
            "actor_email": actor.email,
            "actor_role": actor.role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "source_id": source_id,
            "reason": reason,
            "before_state": before,
            "after_state": after,
        }
        if request_id:
            payload["request_id"] = request_id
        self.insert("knowledge_audit_log", payload)

    def upload_source(self, bucket: str, path: str, payload: bytes, content_type: str):
        if not self.secret:
            raise AdminStorageError("Source upload requires SUPABASE_SERVICE_ROLE_KEY")
        headers = {
            "apikey": self.secret,
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        try:
            response = requests.post(
                f"{self.url}/storage/v1/object/{bucket}/{path}",
                headers=headers,
                data=payload,
                timeout=120,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = exc.response.text[:500] if getattr(exc, "response", None) else str(exc)
            raise AdminStorageError(detail) from exc

    def download_source(self, bucket: str, path: str) -> bytes:
        if not self.secret:
            raise AdminStorageError("Source download requires SUPABASE_SERVICE_ROLE_KEY")
        headers = {
            "apikey": self.secret,
            "Authorization": f"Bearer {self.secret}",
        }
        try:
            response = requests.get(
                f"{self.url}/storage/v1/object/authenticated/{bucket}/{path}",
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            detail = exc.response.text[:500] if getattr(exc, "response", None) else str(exc)
            raise AdminStorageError(detail) from exc

    def signed_source_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        if not self.secret:
            raise AdminStorageError("Signed source URLs require SUPABASE_SERVICE_ROLE_KEY")
        try:
            response = requests.post(
                f"{self.url}/storage/v1/object/sign/{bucket}/{path}",
                headers=self.headers,
                json={"expiresIn": expires_in},
                timeout=45,
            )
            response.raise_for_status()
            signed_path = response.json()["signedURL"]
            if signed_path.startswith("http"):
                return signed_path
            if signed_path.startswith("/storage/v1/"):
                return f"{self.url}{signed_path}"
            return f"{self.url}/storage/v1{signed_path}"
        except (KeyError, requests.RequestException) as exc:
            detail = (
                exc.response.text[:500]
                if getattr(exc, "response", None) is not None
                else str(exc)
            )
            raise AdminStorageError(detail) from exc

    def auth_users(self) -> list[dict]:
        if not self.secret:
            return self._db_fetchall(
                """
                select
                    id::text,
                    email,
                    raw_user_meta_data as user_metadata,
                    raw_app_meta_data as app_metadata,
                    created_at::text,
                    last_sign_in_at::text,
                    banned_until::text
                from auth.users
                order by created_at desc
                """
            )
        try:
            response = requests.get(
                f"{self.url}/auth/v1/admin/users",
                headers={
                    "apikey": self.secret,
                    "Authorization": f"Bearer {self.secret}",
                },
                params={"page": 1, "per_page": 1000},
                timeout=45,
            )
            response.raise_for_status()
            return response.json().get("users", [])
        except requests.RequestException as exc:
            detail = exc.response.text[:500] if getattr(exc, "response", None) else str(exc)
            raise AdminStorageError(detail) from exc

    def update_auth_user(self, user_id: str, payload: dict) -> dict:
        if not self.secret:
            raise AdminStorageError("Auth user updates require SUPABASE_SERVICE_ROLE_KEY")
        try:
            response = requests.put(
                f"{self.url}/auth/v1/admin/users/{user_id}",
                headers=self.headers,
                json=payload,
                timeout=45,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            detail = exc.response.text[:500] if getattr(exc, "response", None) else str(exc)
            raise AdminStorageError(detail) from exc

    def _db_upsert_admin_user(self, payload: dict | None) -> list[dict]:
        if not payload:
            raise AdminStorageError("Missing admin user payload")
        sql = """
            insert into public.admin_users (user_id, role, active)
            values (%s, %s, %s)
            on conflict (user_id)
            do update set role = excluded.role, active = excluded.active, updated_at = now()
            returning *
        """
        return self._db_write_returning(
            sql,
            (payload.get("user_id"), payload.get("role"), payload.get("active")),
        )


class _JsonResponse:
    def __init__(self, payload: Any):
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def get_admin_client() -> SupabaseAdminClient:
    return SupabaseAdminClient()
