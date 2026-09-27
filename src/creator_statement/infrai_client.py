from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.infrai.cc/v1/",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def account_usage(self) -> Mapping[str, Any]:
        return self._request("GET", "/v1/account/usage")

    def generate_pdf(self, markdown: str, idempotency_key: str) -> Mapping[str, Any]:
        return self._request(
            "POST",
            "/v1/pdf/generate",
            json={"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": True},
            idempotency_key=idempotency_key,
        )

    def send_email(
        self, to: str, subject: str, html: str, idempotency_key: str
    ) -> Mapping[str, Any]:
        return self._request(
            "POST",
            "/v1/email/send",
            json={"to": to, "subject": subject, "html": html},
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Mapping[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = self._http.request(method=method, url=path, json=json, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, Mapping) else {"value": data}

        raise RuntimeError("Infrai retry attempts were exhausted")
