"""File virus scanning service. Uses ClamAV if available, otherwise passes through."""
import logging
from dataclasses import dataclass

logger = logging.getLogger("neurohub.virus_scan")


@dataclass
class ScanResult:
    is_clean: bool
    scanner: str
    detail: str


def is_scanning_enabled() -> bool:
    """Check if ClamAV is available for scanning."""
    try:
        import clamd
        cd = clamd.ClamdUnixSocket()
        cd.ping()
        return True
    except Exception:
        return False


def scan_result_for_file(file_content: bytes) -> ScanResult:
    """Scan file content for viruses. Returns clean if no scanner available."""
    try:
        import clamd
        cd = clamd.ClamdUnixSocket()
        cd.ping()
        result = cd.instream(file_content)
        status = result.get("stream", ("OK", ""))[0]
        if status == "OK":
            return ScanResult(is_clean=True, scanner="clamav", detail="Clean")
        else:
            detail = result.get("stream", ("", "Unknown"))[1]
            logger.warning("Virus detected: %s", detail)
            return ScanResult(is_clean=False, scanner="clamav", detail=detail)
    except ImportError:
        logger.debug("ClamAV not available, skipping scan")
        return ScanResult(is_clean=True, scanner="none", detail="Scanner not available")
    except Exception as e:
        logger.warning("Scan failed: %s", e)
        return ScanResult(is_clean=True, scanner="error", detail=str(e))
