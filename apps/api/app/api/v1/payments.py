"""Payment endpoints for Toss Payments integration."""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.payment import Payment
from app.models.service import ServiceDefinition
from app.schemas.payment import (
    PaymentCancelRequest,
    PaymentConfirm,
    PaymentConfirmResponse,
    PaymentListResponse,
    PaymentPrepare,
    PaymentPrepareResponse,
    PaymentRead,
)

router = APIRouter(tags=["Payments"])


def _payment_to_read(p: Payment) -> PaymentRead:
    return PaymentRead(
        id=p.id,
        order_id=p.order_id,
        payment_key=p.payment_key,
        amount=float(p.amount),
        currency=p.currency,
        status=p.status,
        method=p.method,
        request_id=p.request_id,
        confirmed_at=p.confirmed_at,
        created_at=p.created_at,
    )


@router.post("/payments/prepare", response_model=PaymentPrepareResponse)
async def prepare_payment(
    body: PaymentPrepare,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Create a payment record (PENDING) and return Toss SDK params."""
    # Verify service exists
    svc_result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == body.service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    if not svc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Service not found")

    order_id = f"nh-{secrets.token_hex(8)}"
    customer_key = f"nh-user-{str(user.id).replace('-', '')[:12]}"

    payment = Payment(
        institution_id=user.institution_id,
        user_id=user.id,
        request_id=body.request_id,
        order_id=order_id,
        amount=body.amount,
        currency="KRW",
        status="PENDING",
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)

    return PaymentPrepareResponse(
        payment_id=payment.id,
        order_id=order_id,
        amount=float(payment.amount),
        currency="KRW",
        customer_key=customer_key,
    )


@router.post("/payments/confirm", response_model=PaymentConfirmResponse)
async def confirm_payment(
    body: PaymentConfirm,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Verify amount, call Toss API, update payment to CONFIRMED."""
    result = await db.execute(
        select(Payment).where(
            Payment.order_id == body.order_id,
            Payment.institution_id == user.institution_id,
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Payment is {payment.status}, not PENDING")

    # Verify amount matches (prevent client-side tampering)
    if float(payment.amount) != body.amount:
        payment.status = "FAILED"
        payment.failed_at = datetime.now(timezone.utc)
        payment.error_detail = "Amount mismatch"
        await db.flush()
        raise HTTPException(status_code=400, detail="Amount mismatch")

    # Call Toss Payments API
    from app.services.toss_payments import TossPaymentsClient

    toss = TossPaymentsClient()
    try:
        toss_response = await toss.confirm_payment(
            payment_key=body.payment_key,
            order_id=body.order_id,
            amount=int(body.amount),
        )
    except Exception as exc:
        payment.status = "FAILED"
        payment.failed_at = datetime.now(timezone.utc)
        payment.error_detail = str(exc)[:2000]
        await db.flush()
        raise HTTPException(status_code=502, detail=f"Toss API error: {exc}") from exc

    payment.status = "CONFIRMED"
    payment.payment_key = body.payment_key
    payment.method = toss_response.get("method")
    payment.toss_response = toss_response
    payment.confirmed_at = datetime.now(timezone.utc)
    await db.flush()

    return PaymentConfirmResponse(
        payment_id=payment.id,
        status="CONFIRMED",
        method=payment.method,
        receipt_url=toss_response.get("receipt", {}).get("url") if isinstance(toss_response.get("receipt"), dict) else None,
    )


@router.get("/payments/history", response_model=PaymentListResponse)
async def get_payment_history(
    db: DbSession,
    user: AuthenticatedUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List user's payment history."""
    result = await db.execute(
        select(Payment)
        .where(
            Payment.user_id == user.id,
            Payment.institution_id == user.institution_id,
        )
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    payments = result.scalars().all()
    return PaymentListResponse(items=[_payment_to_read(p) for p in payments])


@router.get("/payments/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.institution_id == user.institution_id,
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return _payment_to_read(payment)


@router.post("/payments/{payment_id}/cancel", response_model=PaymentRead)
async def cancel_payment(
    payment_id: uuid.UUID,
    body: PaymentCancelRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Cancel/refund a payment via Toss API."""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.institution_id == user.institution_id,
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status != "CONFIRMED":
        raise HTTPException(status_code=409, detail="Only CONFIRMED payments can be cancelled")

    if not payment.payment_key:
        raise HTTPException(status_code=409, detail="No payment key for cancellation")

    from app.services.toss_payments import TossPaymentsClient

    toss = TossPaymentsClient()
    try:
        await toss.cancel_payment(payment.payment_key, body.reason)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Toss cancel error: {exc}") from exc

    payment.status = "REFUNDED"
    await db.flush()
    await db.refresh(payment)
    return _payment_to_read(payment)
