from datetime import date

import pytest

from creator_statement.statement_service import UsageStatementRequest, send_statement


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def account_usage(self) -> dict[str, object]:
        self.calls.append(("usage", None))
        return {"asset_delivery": 42, "subscriber_updates": 7, "content_processing": 13}

    def generate_pdf(self, markdown: str, idempotency_key: str) -> dict[str, object]:
        self.calls.append(("pdf", (markdown, idempotency_key)))
        return {"document_id": "statement-jan"}

    def send_email(
        self, to: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, object]:
        self.calls.append(("email", (to, subject, html, idempotency_key)))
        return {"message_id": "msg-jan"}


def statement_request(period_end: date) -> UsageStatementRequest:
    return UsageStatementRequest(
        customer_name="Northwind Creator",
        customer_email="ops@example.com",
        period_start=date(2026, 1, 1),
        period_end=period_end,
    )


def test_completed_month_flows_from_usage_to_pdf_and_email() -> None:
    client = RecordingClient()

    result = send_statement(
        statement_request(date(2026, 1, 31)), client, today=date(2026, 2, 10)
    )

    assert result.message_id == "msg-jan"
    assert [name for name, _ in client.calls] == ["usage", "pdf", "email"]
    pdf_markdown = client.calls[1][1][0]
    email_html = client.calls[2][1][2]
    assert '"asset_delivery": 42' in pdf_markdown
    assert '&quot;asset_delivery&quot;: 42' in email_html


def test_current_month_is_not_sent_or_rendered() -> None:
    client = RecordingClient()

    with pytest.raises(ValueError, match="completed calendar period"):
        send_statement(
            statement_request(date(2026, 2, 28)), client, today=date(2026, 2, 10)
        )

    assert client.calls == []

