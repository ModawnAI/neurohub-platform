"""PACS Service — pynetdicom SCP for receiving DICOM via C-STORE (DIMSE)."""

import asyncio
import logging
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Optional

import pydicom

from app.config import settings

logger = logging.getLogger("neurohub.pacs")

# ---------------------------------------------------------------------------
# Module-level SCP state
# ---------------------------------------------------------------------------

_scp_server = None          # pynetdicom transport server (returned by ae.start_server)
_scp_thread: Optional[threading.Thread] = None
_scp_institution_id: Optional[uuid.UUID] = None
_scp_running = False


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def _make_handle_store(institution_id: uuid.UUID):
    """Factory: returns a C-STORE handler bound to *institution_id*."""

    def handle_store(event):
        """Handle an incoming C-STORE request."""
        try:
            ds = event.dataset
            ds.file_meta = event.file_meta

            # Write to a temp file so store_dicom_instance can read bytes
            with tempfile.NamedTemporaryFile(suffix=".dcm", delete=False) as tmp:
                ds.save_as(tmp.name, write_like_original=False)
                tmp_path = tmp.name

            dicom_bytes = Path(tmp_path).read_bytes()
            Path(tmp_path).unlink(missing_ok=True)

            # Schedule async storage on the running event loop (best-effort)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    from app.services.dicom_service import store_dicom_instance  # lazy import
                    asyncio.run_coroutine_threadsafe(
                        store_dicom_instance(
                            dicom_bytes,
                            institution_id,
                            received_via="C_STORE",
                            source_ae_title=event.assoc.requestor.ae_title,
                        ),
                        loop,
                    )
                else:
                    logger.warning("No running event loop; DICOM instance not persisted.")
            except RuntimeError:
                logger.warning("Could not obtain event loop for C-STORE persistence.")

            return 0x0000  # Success

        except Exception:
            logger.exception("Error handling C-STORE request")
            return 0xC001  # Processing failure

    return handle_store


def _make_handle_find(institution_id: uuid.UUID):
    """Factory: returns a C-FIND handler (basic Study Root worklist)."""

    def handle_find(event):
        """Handle a C-FIND request — yield matching DicomStudy identifiers."""
        # Minimal implementation: yield empty dataset (no match)
        # Full implementation would query the database for matching studies.
        logger.info(
            "C-FIND request from %s (institution=%s)",
            event.assoc.requestor.ae_title,
            institution_id,
        )
        yield 0xFF00, pydicom.Dataset()  # Pending — zero results

    return handle_find


# ---------------------------------------------------------------------------
# DicomSCP class
# ---------------------------------------------------------------------------

class DicomSCP:
    """Wraps a pynetdicom Application Entity acting as a Storage SCP."""

    def __init__(self, institution_id: uuid.UUID):
        self.institution_id = institution_id
        self._server = None

    def start(self):
        """Start the DICOM SCP in blocking mode (call from a background thread)."""
        from pynetdicom import AE, evt, StoragePresentationContexts
        from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind

        ae = AE(ae_title=settings.dicom_scp_ae_title)
        ae.supported_contexts = StoragePresentationContexts
        ae.add_supported_context(StudyRootQueryRetrieveInformationModelFind)

        handlers = [
            (evt.EVT_C_STORE, _make_handle_store(self.institution_id)),
            (evt.EVT_C_FIND, _make_handle_find(self.institution_id)),
        ]

        logger.info(
            "Starting DICOM SCP on port %d, AE title '%s', institution=%s",
            settings.dicom_scp_port,
            settings.dicom_scp_ae_title,
            self.institution_id,
        )
        self._server = ae.start_server(
            ("0.0.0.0", settings.dicom_scp_port),
            block=True,            # blocks until shutdown() called
            evt_handlers=handlers,
        )

    def stop(self):
        """Stop the SCP."""
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                logger.exception("Error shutting down DICOM SCP")
            self._server = None


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def start_scp(institution_id: uuid.UUID) -> None:
    """Start the DICOM SCP listener in a background thread."""
    global _scp_server, _scp_thread, _scp_institution_id, _scp_running

    if _scp_running:
        logger.info("DICOM SCP already running; ignoring start request.")
        return

    _scp_institution_id = institution_id
    scp = DicomSCP(institution_id)
    _scp_server = scp

    def _run():
        scp.start()

    _scp_thread = threading.Thread(target=_run, name="dicom-scp", daemon=True)
    _scp_thread.start()
    _scp_running = True
    logger.info("DICOM SCP thread started (institution=%s)", institution_id)


async def stop_scp() -> None:
    """Stop the DICOM SCP listener."""
    global _scp_server, _scp_thread, _scp_running

    if not _scp_running or _scp_server is None:
        logger.info("DICOM SCP not running; ignoring stop request.")
        return

    _scp_server.stop()
    if _scp_thread is not None:
        _scp_thread.join(timeout=10)
        _scp_thread = None

    _scp_server = None
    _scp_running = False
    logger.info("DICOM SCP stopped.")


def get_scp_status() -> dict:
    """Return current SCP status as a dict."""
    return {
        "running": _scp_running,
        "port": settings.dicom_scp_port,
        "ae_title": settings.dicom_scp_ae_title,
        "institution_id": str(_scp_institution_id) if _scp_institution_id else None,
    }
