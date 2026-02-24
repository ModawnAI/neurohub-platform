"""Toss Payments V2 async HTTP client."""

import base64
import logging

import httpx

from app.config import settings

logger = logging.getLogger("neurohub.toss")


class TossPaymentsClient:
    BASE_URL = "https://api.tosspayments.com/v1"

    def _auth_header(self) -> str:
        """Basic auth: base64(secret_key + ':')"""
        token = base64.b64encode(f"{settings.toss_secret_key}:".encode()).decode()
        return f"Basic {token}"

    async def confirm_payment(
        self, payment_key: str, order_id: str, amount: int
    ) -> dict:
        """Confirm a payment with Toss Payments API."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.BASE_URL}/payments/confirm",
                json={
                    "paymentKey": payment_key,
                    "orderId": order_id,
                    "amount": amount,
                },
                headers={
                    "Authorization": self._auth_header(),
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            msg = error.get("message", resp.text[:500])
            logger.error("Toss confirm failed: %s %s", resp.status_code, msg)
            raise Exception(f"Toss confirm failed ({resp.status_code}): {msg}")

        return resp.json()

    async def cancel_payment(self, payment_key: str, reason: str) -> dict:
        """Cancel/refund a payment."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.BASE_URL}/payments/{payment_key}/cancel",
                json={"cancelReason": reason},
                headers={
                    "Authorization": self._auth_header(),
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            msg = error.get("message", resp.text[:500])
            logger.error("Toss cancel failed: %s %s", resp.status_code, msg)
            raise Exception(f"Toss cancel failed ({resp.status_code}): {msg}")

        return resp.json()

    async def get_payment(self, payment_key: str) -> dict:
        """Retrieve payment info."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.BASE_URL}/payments/{payment_key}",
                headers={"Authorization": self._auth_header()},
            )

        if resp.status_code != 200:
            raise Exception(f"Toss get payment failed ({resp.status_code})")

        return resp.json()
