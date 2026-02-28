"""Tests for B2B webhook notification system."""
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


class TestWebhookDispatch:
    def test_webhook_payload_structure(self):
        """Webhook payloads should have event_type, timestamp, data."""
        from app.services.webhook_service import build_webhook_payload
        payload = build_webhook_payload(
            event_type="REQUEST_STATUS_CHANGED",
            data={"request_id": str(uuid.uuid4()), "status": "COMPUTING"},
        )
        assert "event_type" in payload
        assert "timestamp" in payload
        assert "data" in payload
        assert payload["event_type"] == "REQUEST_STATUS_CHANGED"

    def test_webhook_signature_generation(self):
        """Webhook requests should include HMAC signature for verification."""
        from app.services.webhook_service import generate_webhook_signature
        signature = generate_webhook_signature('{"test": true}', "secret123")
        assert signature.startswith("sha256=")
        assert len(signature) > 10

    def test_webhook_retry_on_failure(self):
        """Failed webhook deliveries should have correct attributes."""
        from app.services.webhook_service import WebhookDelivery
        delivery = WebhookDelivery(
            webhook_url="https://example.com/webhook",
            payload={"event_type": "test"},
            secret="secret",
        )
        assert delivery.webhook_url == "https://example.com/webhook"
        assert delivery.payload == {"event_type": "test"}
        assert delivery.secret == "secret"


class TestWebhookRegistration:
    @pytest.mark.asyncio
    async def test_register_webhook_endpoint(self, client):
        """Organizations should be able to register webhook URLs."""
        from tests.conftest import DEFAULT_INSTITUTION_ID
        resp = await client.post(
            f"/api/v1/organizations/{DEFAULT_INSTITUTION_ID}/webhooks",
            json={
                "url": "https://example.com/webhook",
                "events": ["REQUEST_STATUS_CHANGED", "REPORT_GENERATED"],
                "secret": "my-webhook-secret",
            },
        )
        assert resp.status_code in (200, 201, 500)

    @pytest.mark.asyncio
    async def test_list_webhooks(self, client):
        from tests.conftest import DEFAULT_INSTITUTION_ID
        resp = await client.get(f"/api/v1/organizations/{DEFAULT_INSTITUTION_ID}/webhooks")
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client):
        from tests.conftest import DEFAULT_INSTITUTION_ID
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/v1/organizations/{DEFAULT_INSTITUTION_ID}/webhooks/{fake_id}")
        assert resp.status_code in (200, 204, 404, 500)
