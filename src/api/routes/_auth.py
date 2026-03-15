from __future__ import annotations

import os

from fastapi import Header, HTTPException


async def require_operator_key(authorization: str = Header(...)) -> None:
    expected = os.environ.get("OPERATOR_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="OPERATOR_API_KEY not configured on server")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing operator API key")
