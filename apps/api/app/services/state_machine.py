from enum import StrEnum

from fastapi import HTTPException, status

from app.dependencies import CurrentUser


class RequestStatus(StrEnum):
    CREATED = "CREATED"
    RECEIVING = "RECEIVING"
    STAGING = "STAGING"
    READY_TO_COMPUTE = "READY_TO_COMPUTE"
    COMPUTING = "COMPUTING"
    QC = "QC"
    REPORTING = "REPORTING"
    EXPERT_REVIEW = "EXPERT_REVIEW"
    FINAL = "FINAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TRANSITIONS: dict[tuple[RequestStatus, RequestStatus], set[str]] = {
    (RequestStatus.CREATED, RequestStatus.RECEIVING): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.RECEIVING, RequestStatus.STAGING): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.STAGING, RequestStatus.READY_TO_COMPUTE): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.READY_TO_COMPUTE, RequestStatus.COMPUTING): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.COMPUTING, RequestStatus.QC): {"SYSTEM_ADMIN"},
    (RequestStatus.QC, RequestStatus.REPORTING): {"REVIEWER", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.QC, RequestStatus.FAILED): {"REVIEWER", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.REPORTING, RequestStatus.EXPERT_REVIEW): {"SYSTEM_ADMIN"},
    (RequestStatus.REPORTING, RequestStatus.FINAL): {"REVIEWER", "SYSTEM_ADMIN"},
    (RequestStatus.EXPERT_REVIEW, RequestStatus.FINAL): {"REVIEWER", "SYSTEM_ADMIN"},
    (RequestStatus.EXPERT_REVIEW, RequestStatus.COMPUTING): {"REVIEWER", "SYSTEM_ADMIN"},
    (RequestStatus.CREATED, RequestStatus.CANCELLED): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.RECEIVING, RequestStatus.CANCELLED): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.STAGING, RequestStatus.CANCELLED): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
    (RequestStatus.READY_TO_COMPUTE, RequestStatus.CANCELLED): {"PHYSICIAN", "TECHNICIAN", "SYSTEM_ADMIN"},
}

TERMINAL_STATES = {RequestStatus.FINAL, RequestStatus.FAILED, RequestStatus.CANCELLED}
FAILED_ALLOWED_ROLES = {"REVIEWER", "TECHNICIAN", "SYSTEM_ADMIN"}


def validate_transition(
    from_status: RequestStatus,
    to_status: RequestStatus,
    actor: CurrentUser | None = None,
) -> None:
    if from_status == to_status:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No-op transition")
    if from_status in TERMINAL_STATES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transition from terminal state denied")

    if to_status == RequestStatus.FAILED:
        if actor is None:
            return
        if not actor.has_any_role(*FAILED_ALLOWED_ROLES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(sorted(FAILED_ALLOWED_ROLES))}",
            )
        return

    key = (from_status, to_status)
    if key not in TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid transition: {from_status} -> {to_status}",
        )

    if actor is None:
        return

    allowed = TRANSITIONS[key]
    if not actor.has_any_role(*allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required roles: {', '.join(sorted(allowed))}",
        )
