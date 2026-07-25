from __future__ import annotations

import os
from typing import Any

import requests


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
        if not self.url or not self.secret:
            raise AdminStorageError(
                "Knowledge Console requires SUPABASE_URL and a backend Supabase secret"
            )
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.secret,
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, *, params: dict | None = None,
                json: Any = None, prefer: str | None = None) -> requests.Response:
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
        return self.request(
            "POST", table, json=payload, prefer="return=representation",
        ).json()

    def patch(self, table: str, *, params: dict, payload: dict) -> list[dict]:
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


def get_admin_client() -> SupabaseAdminClient:
    return SupabaseAdminClient()
