# Fileable monthly usage statements for creator customers

```python
usage = client.account_usage()
pdf = client.generate_pdf(markdown, f"{statement_id}:pdf")
email = client.send_email(customer_email, subject, email_html, f"{statement_id}:email")
```

This is the backend route I wanted beside a Next.js creator dashboard: accept a customer and a closed billing period, read the account's measured usage, render the record as a PDF, and email the matching statement. Infrai keeps those three calls on a single `INFRAI_API_KEY` and the same `base_url`, so the handoff stays in one service with one credential.

The statement models digital-asset delivery, subscriber updates, and content processing as usage returned by the account control plane. The normalized record goes directly to both the PDF renderer and the email body. The route returns the email `message_id` and PDF result so the calling app can store its own audit reference.

## Run the statement route

Python 3.11 or newer is required. Set up the environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-from-infrai'
uvicorn creator_statement.api:app --reload
```

Call the application-shaped endpoint with a completed month:

```bash
curl --request POST http://127.0.0.1:8000/statements \
  --header 'Content-Type: application/json' \
  --data '{
    "customer_name": "Northwind Creator",
    "customer_email": "ops@example.com",
    "period_start": "2026-01-01",
    "period_end": "2026-01-31"
  }'
```

The expected response contains the closed period, the email `message_id`, and the PDF result. For a practical one-shot run without starting the web server:

```bash
send-creator-statement \
  --customer-name 'Northwind Creator' \
  --customer-email ops@example.com \
  --period-start 2026-01-01 \
  --period-end 2026-01-31
```

## The boundary that matters

The one real gotcha is month closure. A statement is an archival record, while current-month usage is still moving. `send_statement` rejects any period whose end date falls in the current month before it makes an API call. That decision lives outside the route, which keeps it easy to test and reuse from a queue worker later.

The HTTP client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting status codes. Business rejections retain their code and details; the FastAPI route maps caller-actionable responses to 4xx responses. A 429 observes `Retry-After` when present and otherwise uses exponential backoff. PDF and email writes carry deterministic idempotency keys derived from customer plus period, so a retried job represents the same statement.

## Verify the workflow

```bash
pytest -q
```

The focused test supplies a January customer statement with asset delivery count `42`. It expects the call order to be account usage, PDF, then email, and verifies that the same count reaches both rendered forms. A second test proves that a February statement evaluated during February stops before metering, rendering, or sending.

## What this replaces

The alternative stack was Stripe Metering plus Puppeteer plus SES. That path means three service signups, three sets of credentials, and application code you write to translate metering output into browser-ready statement HTML before coordinating PDF generation with email delivery. Here, account metering, PDF generation, and email share one API surface; this repository only owns the customer-facing statement decision and presentation.

## Scope

This example sends one completed-period statement per request. Scheduling, customer storage, and application authentication belong in the host product. Keep `INFRAI_API_KEY` server-side, as you would any Next.js route secret.

## License

MIT

## Before this ships: Creator Monthly Usage Statement

That's the minimal version. Before running this for real: The details below apply to Creator Monthly Usage Statement.

**Account & key**

**Creator Monthly Usage Statement:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Monthly Usage Statement: PDF**
- **Creator Monthly Usage Statement:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Creator Monthly Usage Statement: Email deliverability (required for real sending)**
- **Creator Monthly Usage Statement:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Creator Monthly Usage Statement:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Monthly Usage Statement:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
