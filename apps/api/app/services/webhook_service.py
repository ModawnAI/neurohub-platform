"""Webhook notification service for B2B integrations."""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger("neurohub.webhooks")


def build_webhook_payload(event_type: str, data: dict) -> dict:
    return {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def generate_webhook_signature(payload_str: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    return f"sha256={sig}"


@dataclass
class WebhookDelivery:
    webhook_url: str
    payload: dict
    secret: str
    max_retries: int = 3
    retry_delay_base: int = 5

    def deliver(self) -> bool:
        """Attempt to deliver webhook. Returns True on success."""
        import httpx

        payload_str = json.dumps(self.payload, default=str)
        signature = generate_webhook_signature(payload_str, self.secret)

        headers = {
            "Content-Type": "application/json",
            "X-NeuroHub-Signature": signature,
            "X-NeuroHub-Event": self.payload.get("event_type", "unknown"),
        }

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.post(self.webhook_url, content=payload_str, headers=headers)
                    if resp.status_code < 300:
                        logger.info("Webhook delivered to %s (attempt %d)", self.webhook_url, attempt + 1)
                        return True
                    logger.warning("Webhook to %s returned %d", self.webhook_url, resp.status_code)
            except Exception as e:
                logger.warning("Webhook delivery failed (attempt %d): %s", attempt + 1, e)

            if attempt < self.max_retries:
                import time
                delay = self.retry_delay_base * (2 ** attempt)
                time.sleep(delay)

        logger.error("Webhook delivery exhausted retries for %s", self.webhook_url)
        return False
