"""Custom exception classes for NeuroHub API.

All exceptions extend NeuroHubError and provide structured error responses
with error codes for client consumption.
"""


class NeuroHubError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(NeuroHubError):
    def __init__(self, resource: str, resource_id: str | None = None):
        detail = {"resource": resource}
        if resource_id:
            detail["resource_id"] = resource_id
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found",
            status_code=404,
            detail=detail,
        )


class ConflictError(NeuroHubError):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
            detail=detail,
        )


class ForbiddenError(NeuroHubError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


class ValidationError(NeuroHubError):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            detail=detail,
        )


class RateLimitError(NeuroHubError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMITED",
            message="Too many requests. Please try again later.",
            status_code=429,
            detail={"retry_after": retry_after},
        )
