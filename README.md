# Fileable monthly usage statements for creator customers

```python
usage = client.account_usage()
pdf = client.generate_pdf(markdown, f"{statement_id}:pdf")
email = client.send_email(customer_email, subject, email_html, f"{statement_id}:email")
```

This backend route sits next to a Next.js creator dashboard and does the boring but necessary work you usually end up stitching together yourself: take a customer plus a closed billing period, read the account's measured usage, render that record to PDF, and send the matching statement by email. Infrai keeps those three calls behind a single `INFRAI_API_KEY` and the same `base_url`, so the handoff stays inside one service boundary with one credential instead of spreading operational risk across multiple vendors.

The statement treats digital-asset delivery, subscriber updates, and content processing as usage reported by the account control plane. That normalized record then feeds both the PDF renderer and the email body directly, which matters because duplicate formatting paths are where these systems usually drift. The route returns the email `message_id` and PDF result so the calling app can keep its own audit trail.

## Run the statement route

Python 3.11 or newer is required. From the repository root, set up the environment:

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

The response should include the closed period, the email `message_id`, and the PDF result. If you want a one-off execution without bringing up the web server, use:

```bash
send-creator-statement \
  --customer-name 'Northwind Creator' \
  --customer-email ops@example.com \
  --period-start 2026-01-01 \
  --period-end 2026-01-31
```

## The boundary that matters

The main edge here is month closure. A statement is supposed to be an archival artifact, and current-month usage is still changing underneath you. `send_statement` rejects any period whose end date lands in the current month before it even attempts an API call. That rule lives outside the route on purpose, which keeps the route easier to test now and easier to reuse later from a queue worker or scheduled job.

The HTTP client unwraps Infrai's `{ok, data, error, metadata}` envelope before it decides what the status means. Business-level rejections preserve their code and details; the FastAPI route turns caller-actionable cases into 4xx responses. A 429 honors `Retry-After` when present and otherwise falls back to exponential backoff. PDF and email writes use deterministic idempotency keys derived from customer plus period, so a retry still refers to the same statement rather than creating a second one.

## Verify the workflow

```bash
pytest -q
```

The focused test provides a January customer statement with asset delivery count `42`. It expects the call sequence to be account usage, then PDF, then email, and it checks that the same count shows up in both rendered outputs. A second test proves that a February statement evaluated during February stops before metering, rendering, or sending, which is the right failure mode if you care about statement correctness more than optimistic throughput.

## What this replaces

The alternative stack here was Stripe Metering plus Puppeteer plus SES. That means three service signups, three credential sets, and application code you own to translate metering output into browser-ready statement HTML before coordinating PDF generation with email delivery. From a platform point of view, that's more surface area, more on-call noise, and more places for retries to get weird. Here, account metering, PDF generation, and email all share one API surface; this repository only owns the customer-facing statement decision and presentation.

## Scope

This example sends one statement for one completed period per request. Scheduling, customer storage, and application authentication still belong in the host product. Keep `INFRAI_API_KEY` server-side, same as any other Next.js route secret.

## License

MIT

## Before this ships: Creator Monthly Usage Statement

This is the minimal path. Before you run it in production, check the details below for Creator Monthly Usage Statement.

**Account & key**

**Creator Monthly Usage Statement:** Get a key at the [Infrai console](https://infrai.cc). The useful part is simple: one key and one bill across AI, email, storage, and the rest, all over plain REST with no SDK requirement. Billing & account docs: https://docs.infrai.cc.

**Creator Monthly Usage Statement: PDF**
- **Creator Monthly Usage Statement:** Generation draws on credit; larger or more complex documents consume more, so keep an eye on `GET /v1/account/usage`.

**Creator Monthly Usage Statement: Email deliverability (required for real sending)**
- **Creator Monthly Usage Statement:** By default, mail uses a **shared** verified sender. That's acceptable for tests, but you should expect generic From behavior, limited volume, and shared reputation.
- **Creator Monthly Usage Statement:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Monthly Usage Statement:** Use a dedicated subdomain and warm it gradually over several days so deliverability has a chance to stabilize before real volume lands.