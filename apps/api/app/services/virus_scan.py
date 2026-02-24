"""File virus scanning service using ClamAV with quarantine and audit logging."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger("neurohub.virus_scan")


@dataclass
class ScanResult:
    is_clean: bool
    scanner: str
    detail: str
    scanned_at: str | None = None


def is_scanning_enabled() -> bool:
    """Check if ClamAV is available for scanning."""
    try:
        import clamd

        cd = clamd.ClamdUnixSocket()
        cd.ping()
        return True
    except Exception:
        return False


def scan_file(file_content: bytes, *, filename: str = "unknown") -> ScanResult:
    """Scan file content for viruses. Returns clean if no scanner available."""
    scanned_at = datetime.now(timezone.utc).isoformat()
    try:
        import clamd

        cd = clamd.ClamdUnixSocket()
        cd.ping()
        result = cd.instream(file_content)
        scan_status = result.get("stream", ("OK", ""))[0]
        if scan_status == "OK":
            logger.info("File %s scanned clean by ClamAV", filename)
            return ScanResult(
                is_clean=True,
                scanner="clamav",
                detail="Clean",
                scanned_at=scanned_at,
            )
        else:
            detail = result.get("stream", ("", "Unknown"))[1]
            logger.warning("Virus detected in %s: %s", filename, detail)
            return ScanResult(
                is_clean=False,
                scanner="clamav",
                detail=detail,
                scanned_at=scanned_at,
            )
    except ImportError:
        logger.debug("ClamAV not available, skipping scan")
        return ScanResult(
            is_clean=True,
            scanner="none",
            detail="Scanner not available",
            scanned_at=scanned_at,
        )
    except Exception as e:
        logger.warning("Scan failed for %s: %s", filename, e)
        return ScanResult(
            is_clean=True,
            scanner="error",
            detail=str(e),
            scanned_at=scanned_at,
        )


# Keep backward compat alias
scan_result_for_file = scan_file


def quarantine_file(
    *,
    institution_id: str,
    request_id: str,
    filename: str,
    scan_result: ScanResult,
) -> str:
    """Move infected file to quarantine storage path.

    Returns the quarantine path. The actual file content is NOT stored —
    only metadata is logged for security review.
    """
    quarantine_path = (
        f"quarantine/{institution_id}/{request_id}/"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{filename}"
    )
    logger.warning(
        "File quarantined: %s (threat: %s) -> %s",
        filename,
        scan_result.detail,
        quarantine_path,
    )
    return quarantine_path


def log_scan_to_audit(
    session,
    *,
    institution_id,
    request_id,
    filename: str,
    scan_result: ScanResult,
    quarantine_path: str | None = None,
) -> None:
    """Log virus scan result to the audit trail (outbox event).

    Works in sync session context (Celery tasks).
    """
    from app.models.outbox import OutboxEvent

    session.add(
        OutboxEvent(
            event_type="FILE_SCAN_COMPLETED" if scan_result.is_clean else "FILE_QUARANTINED",
            aggregate_type="request",
            aggregate_id=request_id if isinstance(request_id, uuid.UUID) else uuid.UUID(request_id),
            payload={
                "filename": filename,
                "scanner": scan_result.scanner,
                "is_clean": scan_result.is_clean,
                "detail": scan_result.detail,
                "scanned_at": scan_result.scanned_at,
                "quarantine_path": quarantine_path,
            },
        )
    )


async def log_scan_to_audit_async(
    db,
    *,
    institution_id,
    request_id,
    filename: str,
    scan_result: ScanResult,
    quarantine_path: str | None = None,
) -> None:
    """Async version of audit logging for FastAPI endpoints."""
    from app.models.outbox import OutboxEvent

    db.add(
        OutboxEvent(
            event_type="FILE_SCAN_COMPLETED" if scan_result.is_clean else "FILE_QUARANTINED",
            aggregate_type="request",
            aggregate_id=request_id if isinstance(request_id, uuid.UUID) else uuid.UUID(request_id),
            payload={
                "filename": filename,
                "scanner": scan_result.scanner,
                "is_clean": scan_result.is_clean,
                "detail": scan_result.detail,
                "scanned_at": scan_result.scanned_at,
                "quarantine_path": quarantine_path,
            },
        )
    )
