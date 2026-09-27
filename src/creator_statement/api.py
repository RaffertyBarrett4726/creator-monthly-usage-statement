from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .statement_service import UsageStatementRequest, UsageStatementResult, send_statement

app = FastAPI(title="Creator usage statements")


@app.post("/statements", response_model=UsageStatementResult)
def create_statement(request: UsageStatementRequest) -> UsageStatementResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")

    client = InfraiClient(api_key=api_key)
    try:
        return send_statement(request, client)
    except InfraiError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        client.close()

