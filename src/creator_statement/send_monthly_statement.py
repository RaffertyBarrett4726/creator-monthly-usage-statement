from __future__ import annotations

import argparse
import json
import os
from datetime import date

from .infrai_client import InfraiClient
from .statement_service import UsageStatementRequest, send_statement


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a completed monthly usage statement")
    parser.add_argument("--customer-name", required=True)
    parser.add_argument("--customer-email", required=True)
    parser.add_argument("--period-start", required=True, type=date.fromisoformat)
    parser.add_argument("--period-end", required=True, type=date.fromisoformat)
    args = parser.parse_args()

    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        parser.error("INFRAI_API_KEY is required")

    request = UsageStatementRequest(
        customer_name=args.customer_name,
        customer_email=args.customer_email,
        period_start=args.period_start,
        period_end=args.period_end,
    )
    client = InfraiClient(api_key=api_key)
    try:
        result = send_statement(request, client)
        print(json.dumps(result.model_dump(), indent=2, default=str))
    finally:
        client.close()


if __name__ == "__main__":
    main()

