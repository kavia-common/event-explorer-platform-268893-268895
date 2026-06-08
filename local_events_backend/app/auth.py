from __future__ import annotations

import uuid

from fastapi import Header, HTTPException, status


# PUBLIC_INTERFACE
def require_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> uuid.UUID:
    """Require `X-User-Id` header and parse it as a UUID.

    Args:
        x_user_id: Header value provided by the frontend.

    Returns:
        Parsed UUID representing the caller's identity.

    Raises:
        HTTPException: 401 if missing, 400 if invalid UUID.
    """
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header is required")

    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-Id must be a UUID") from exc
