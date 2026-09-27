from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

try:
    from pydantic import BaseModel, Field, model_validator
except ModuleNotFoundError:
    BaseModel = None


def _validate_request(request: "UsageStatementRequest") -> None:
    if not 1 <= len(request.customer_name) <= 120:
        raise ValueError("customer_name must contain between 1 and 120 characters")
    if not 3 <= len(request.customer_email) <= 254:
        raise ValueError("customer_email must contain between 3 and 254 characters")
    local, separator, domain = request.customer_email.partition("@")
    if not separator or not local or "." not in domain:
        raise ValueError("customer_email must be a valid email address")
    if request.period_end < request.period_start:
        raise ValueError("period_end must be on or after period_start")


if BaseModel is not None:

    class UsageStatementRequest(BaseModel):
        customer_name: str = Field(min_length=1, max_length=120)
        customer_email: str = Field(min_length=3, max_length=254)
        period_start: date
        period_end: date

        @model_validator(mode="after")
        def validate_period(self) -> "UsageStatementRequest":
            _validate_request(self)
            return self


    class UsageStatementResult(BaseModel):
        period: str
        message_id: str
        pdf: dict[str, Any]

else:

    @dataclass
    class UsageStatementRequest:
        customer_name: str
        customer_email: str
        period_start: date
        period_end: date

        def __post_init__(self) -> None:
            _validate_request(self)


    @dataclass
    class UsageStatementResult:
        period: str
        message_id: str
        pdf: dict[str, Any]


class StatementClient(Protocol):
    def account_usage(self) -> dict[str, Any]:
        raise AssertionError("StatementClient is a structural typing contract")

    def generate_pdf(self, markdown: str, idempotency_key: str) -> dict[str, Any]:
        raise AssertionError("StatementClient is a structural typing contract")

    def send_email(
        self, to: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, Any]:
        raise AssertionError("StatementClient is a structural typing contract")


def send_statement(
    request: UsageStatementRequest,
    client: StatementClient,
    *,
    today: date | None = None,
) -> UsageStatementResult:
    clock = today or date.today()
    if request.period_end >= clock.replace(day=1):
        raise ValueError("Statements can only be sent for a completed calendar period")

    period = f"{request.period_start.isoformat()} to {request.period_end.isoformat()}"
    usage = client.account_usage()
    usage_json = json.dumps(usage, indent=2, sort_keys=True, default=str)
    statement_id = hashlib.sha256(
        f"{request.customer_email}:{period}".encode()
    ).hexdigest()[:24]

    markdown = (
        f"# Monthly usage statement\n\n"
        f"Customer: {request.customer_name}\n\n"
        f"Period: {period}\n\n"
        f"## Recorded usage\n\n```json\n{usage_json}\n```\n"
    )
    pdf = client.generate_pdf(markdown, f"{statement_id}:pdf")

    safe_name = html.escape(request.customer_name)
    safe_period = html.escape(period)
    safe_usage = html.escape(usage_json)
    email_html = (
        f"<h1>Monthly usage statement</h1>"
        f"<p>Customer: {safe_name}</p>"
        f"<p>Period: {safe_period}</p>"
        f"<h2>Recorded usage</h2><pre>{safe_usage}</pre>"
        f"<p>Statement reference: {statement_id}</p>"
    )
    email = client.send_email(
        request.customer_email,
        f"Usage statement: {period}",
        email_html,
        f"{statement_id}:email",
    )
    message_id = email.get("message_id")
    if not isinstance(message_id, str) or not message_id:
        raise RuntimeError("Email response did not include message_id")

    return UsageStatementResult(period=period, message_id=message_id, pdf=dict(pdf))
