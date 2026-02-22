"""TDD tests for file upload pipeline (Phase 1).

These tests define the expected behavior for:
- Presigning upload URLs
- Completing uploads with SHA-256 checksums
- Listing case files
- Generating download URLs
- Auto-transition: request CREATED → RECEIVING on first presign
- Validation: upload to correct request/case/institution
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import (
    DEFAULT_INSTITUTION_ID,
    DEFAULT_PIPELINE_ID,
    DEFAULT_SERVICE_ID,
    create_test_request,
)


class TestPresignUpload:
    """POST /api/v1/requests/{req}/cases/{case}/files/presign."""

    async def _get_case_id(self, client, request_id: str) -> str:
        resp = await client.get(f"/api/v1/requests/{request_id}")
        data = resp.json()
        # Request detail should include cases (or we fetch separately)
        cases_resp = await client.get(f"/api/v1/requests/{request_id}/cases")
        return cases_resp.json()["items"][0]["id"]

    @patch("app.services.storage.create_presigned_upload")
    async def test_presign_returns_url_and_file_id(self, mock_presign, client):
        mock_presign.return_value = "https://storage.example.com/upload?token=abc"

        created = await create_test_request(client)
        request_id = created["id"]
        cases_resp = await client.get(f"/api/v1/requests/{request_id}/cases")
        case_id = cases_resp.json()["items"][0]["id"]

        resp = await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/presign",
            json={
                "slot_name": "T1_MRI",
                "file_name": "brain_scan.dcm",
                "content_type": "application/dicom",
                "file_size": 1024000,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "case_file_id" in data
        assert "presigned_url" in data
        assert "expires_at" in data

    @patch("app.services.storage.create_presigned_upload")
    async def test_presign_auto_transitions_to_receiving(self, mock_presign, client):
        mock_presign.return_value = "https://storage.example.com/upload?token=abc"

        created = await create_test_request(client)
        request_id = created["id"]
        assert created["status"] == "CREATED"

        cases_resp = await client.get(f"/api/v1/requests/{request_id}/cases")
        case_id = cases_resp.json()["items"][0]["id"]

        await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/presign",
            json={
                "slot_name": "T1_MRI",
                "file_name": "scan.dcm",
                "content_type": "application/dicom",
                "file_size": 512000,
            },
        )

        req_resp = await client.get(f"/api/v1/requests/{request_id}")
        assert req_resp.json()["status"] == "RECEIVING"

    async def test_presign_nonexistent_request_returns_404(self, client):
        resp = await client.post(
            f"/api/v1/requests/{uuid.uuid4()}/cases/{uuid.uuid4()}/files/presign",
            json={
                "slot_name": "T1_MRI",
                "file_name": "scan.dcm",
                "content_type": "application/dicom",
                "file_size": 512000,
            },
        )
        assert resp.status_code == 404


class TestCompleteUpload:
    """POST /api/v1/requests/{req}/cases/{case}/files/{file}/complete."""

    @patch("app.services.storage.create_presigned_upload")
    async def test_complete_sets_status_and_checksum(self, mock_presign, client):
        mock_presign.return_value = "https://storage.example.com/upload?token=abc"

        created = await create_test_request(client)
        request_id = created["id"]
        cases_resp = await client.get(f"/api/v1/requests/{request_id}/cases")
        case_id = cases_resp.json()["items"][0]["id"]

        presign_resp = await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/presign",
            json={
                "slot_name": "T1_MRI",
                "file_name": "scan.dcm",
                "content_type": "application/dicom",
                "file_size": 512000,
            },
        )
        file_id = presign_resp.json()["case_file_id"]

        resp = await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/{file_id}/complete",
            json={
                "checksum_sha256": "a" * 64,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["upload_status"] == "COMPLETED"
        assert data["checksum_sha256"] == "a" * 64

    @patch("app.services.storage.create_presigned_upload")
    async def test_complete_already_completed_returns_409(self, mock_presign, client):
        mock_presign.return_value = "https://storage.example.com/upload?token=abc"

        created = await create_test_request(client)
        request_id = created["id"]
        cases_resp = await client.get(f"/api/v1/requests/{request_id}/cases")
        case_id = cases_resp.json()["items"][0]["id"]

        presign_resp = await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/presign",
            json={
                "slot_name": "T1_MRI",
                "file_name": "scan.dcm",
                "content_type": "application/dicom",
                "file_size": 512000,
            },
        )
        file_id = presign_resp.json()["case_file_id"]

        # Complete once
        await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/{file_id}/complete",
            json={"checksum_sha256": "a" * 64},
        )
        # Try again
        resp = await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/{file_id}/complete",
            json={"checksum_sha256": "a" * 64},
        )
        assert resp.status_code == 409


class TestListCaseFiles:
    """GET /api/v1/requests/{req}/cases/{case}/files."""

    @patch("app.services.storage.create_presigned_upload")
    async def test_list_files_returns_uploaded_files(self, mock_presign, client):
        mock_presign.return_value = "https://storage.example.com/upload?token=abc"

        created = await create_test_request(client)
        request_id = created["id"]
        cases_resp = await client.get(f"/api/v1/requests/{request_id}/cases")
        case_id = cases_resp.json()["items"][0]["id"]

        # Create a file
        await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/presign",
            json={
                "slot_name": "T1_MRI",
                "file_name": "scan.dcm",
                "content_type": "application/dicom",
                "file_size": 512000,
            },
        )

        resp = await client.get(f"/api/v1/requests/{request_id}/cases/{case_id}/files")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["slot_name"] == "T1_MRI"


class TestListCases:
    """GET /api/v1/requests/{req}/cases."""

    async def test_list_cases_returns_cases(self, client):
        created = await create_test_request(
            client,
            cases=[
                {"patient_ref": "PAT-001"},
                {"patient_ref": "PAT-002"},
            ],
        )
        resp = await client.get(f"/api/v1/requests/{created['id']}/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2


class TestDownloadUrl:
    """GET /api/v1/requests/{req}/cases/{case}/files/{file}/download."""

    @patch("app.services.storage.create_presigned_download")
    @patch("app.services.storage.create_presigned_upload")
    async def test_download_completed_file(self, mock_upload, mock_download, client):
        mock_upload.return_value = "https://storage.example.com/upload?token=abc"
        mock_download.return_value = "https://storage.example.com/download?token=xyz"

        created = await create_test_request(client)
        request_id = created["id"]
        cases_resp = await client.get(f"/api/v1/requests/{request_id}/cases")
        case_id = cases_resp.json()["items"][0]["id"]

        presign_resp = await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/presign",
            json={
                "slot_name": "T1_MRI",
                "file_name": "scan.dcm",
                "content_type": "application/dicom",
                "file_size": 512000,
            },
        )
        file_id = presign_resp.json()["case_file_id"]

        # Complete upload first
        await client.post(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/{file_id}/complete",
            json={"checksum_sha256": "a" * 64},
        )

        resp = await client.get(
            f"/api/v1/requests/{request_id}/cases/{case_id}/files/{file_id}/download"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert "expires_at" in data
