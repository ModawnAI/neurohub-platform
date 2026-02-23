"""Scope validation dependency for API key authentication.

Usage:
    from app.middleware.scope_check import require_scope

    @router.get("/data", dependencies=[Depends(require_scope("read"))])
    async def get_data(...): ...
"""

from fastapi import Depends, HTTPException, status

from app.dependencies import CurrentUser, get_current_user


def require_scope(*scopes: str):
    """FastAPI dependency that checks if the user has the required API key scopes.

    For JWT-authenticated users (no scopes), access is always granted.
    For API key users, all listed scopes must be present.
    """

    async def checker(user: CurrentUser = Depends(get_current_user)):
        for scope in scopes:
            if not user.has_scope(scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key missing required scope: {scope}",
                )
        return user

    return checker
