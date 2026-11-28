from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_request import PaymentRequest
from app.schemas.payment_request import PaymentRequestCreate
from app.services.group_service import lock_group, get_membership
from app.services.ledger_service import calculate_group_balances
from app.services.notification_service import notify


def create_payment_request(
    db: Session,
    group_id: int,
    requester_id: int,
    payload: PaymentRequestCreate,
    idempotency_key: str | None = None,
) -> PaymentRequest:
    try:
        group = lock_group(db, group_id)

        if get_membership(db, group_id, requester_id) is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group",
            )

        if requester_id == payload.debtor_id:
            raise HTTPException(
                status_code=400,
                detail="You cannot request payment from yourself",
            )

        if get_membership(db, group_id, payload.debtor_id) is None:
            raise HTTPException(
                status_code=400,
                detail="Debtor must be a group member",
            )

        if idempotency_key is not None:
            existing = db.scalar(
                select(PaymentRequest).where(
                    PaymentRequest.group_id == group_id,
                    PaymentRequest.requester_id == requester_id,
                    PaymentRequest.idempotency_key == idempotency_key,
                )
            )

            if existing is not None:
                if (
                        existing.debtor_id != payload.debtor_id
                        or existing.amount != payload.amount
                        or existing.description != payload.description
                        or existing.due_date != payload.due_date
                ):
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Idempotency key already used "
                            "for a different payment request"
                        ),
                    )

                db.commit()
                return existing

        if (
            group.currency == "JPY"
            and payload.amount != payload.amount.to_integral_value()
        ):
            raise HTTPException(
                status_code=422,
                detail="JPY amounts must be whole numbers",
            )

        balances = calculate_group_balances(db, group_id)

        requester_balance = balances.get(
            requester_id, Decimal("0.00")
        )

        debtor_balance = balances.get(
            payload.debtor_id, Decimal("0.00")
        )

        if requester_balance <= 0 or debtor_balance >= 0:
            raise HTTPException(
                status_code=409,
                detail="No outstanding balance for this request",
            )

        maximum_amount = min(
            requester_balance,
            -debtor_balance,
        )

        if payload.amount > maximum_amount:
            raise HTTPException(
                status_code=409,
                detail="Request exceeds outstanding balance",
            )

        existing_pending = db.scalar(
            select(PaymentRequest).where(
                PaymentRequest.group_id == group_id,
                PaymentRequest.requester_id == requester_id,
                PaymentRequest.debtor_id == payload.debtor_id,
                PaymentRequest.status == "pending",
            )
        )

        if existing_pending is not None:
            raise HTTPException(
                status_code=409,
                detail="A pending request already exists for this member",
            )

        payment_request = PaymentRequest(
            group_id=group_id,
            requester_id=requester_id,
            debtor_id=payload.debtor_id,
            amount=payload.amount,
            description=payload.description,
            due_date=payload.due_date,
            fulfilled_amount=Decimal("0.00"),
            status="pending",
            idempotency_key=idempotency_key,
        )

        db.add(payment_request)
        db.flush()
        db.refresh(payment_request)
        notify(db, payment_request.debtor_id, f"request-{payment_request.status}:{payment_request.id}", f"Payment request #{payment_request.id}: {payment_request.status}.")
        db.commit()

        return payment_request

    except Exception:
        db.rollback()
        raise


def list_payment_requests(
    db: Session,
    group_id: int,
    user_id: int,
) -> list[PaymentRequest]:
    lock_group(db, group_id)

    if get_membership(db, group_id, user_id) is None:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    return list(
        db.scalars(
            select(PaymentRequest)
            .where(PaymentRequest.group_id == group_id)
            .order_by(
                PaymentRequest.created_at.desc(),
                PaymentRequest.id.desc(),
            )
        ).all()
    )


def cancel_payment_request(
    db: Session,
    group_id: int,
    request_id: int,
    requester_id: int,
) -> PaymentRequest:
    try:
        lock_group(db, group_id)

        if get_membership(db, group_id, requester_id) is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group",
            )

        payment_request = db.scalar(
            select(PaymentRequest).where(
                PaymentRequest.id == request_id,
                PaymentRequest.group_id == group_id,
            )
        )

        if payment_request is None:
            raise HTTPException(
                status_code=404,
                detail="Payment request not found",
            )

        if payment_request.requester_id != requester_id:
            raise HTTPException(
                status_code=403,
                detail="Only the requester can cancel this request",
            )

        if payment_request.status != "pending":
            raise HTTPException(
                status_code=409,
                detail="Only pending requests can be cancelled",
            )

        payment_request.status = "cancelled"
        payment_request.resolved_at = datetime.now(timezone.utc)

        db.flush()
        db.refresh(payment_request)
        notify(db, payment_request.debtor_id, f"request-{payment_request.status}:{payment_request.id}", f"Payment request #{payment_request.id}: {payment_request.status}.")
        db.commit()

        return payment_request

    except Exception:
        db.rollback()
        raise

def reconcile_payment_request(
    db: Session,
    group_id: int,
    sender_id: int,
    recipient_id: int,
    amount: Decimal,
) -> None:
    payment_request = db.scalar(
        select(PaymentRequest).where(
            PaymentRequest.group_id == group_id,
            PaymentRequest.requester_id == recipient_id,
            PaymentRequest.debtor_id == sender_id,
            PaymentRequest.status == "pending",
        )
    )

    if payment_request is None:
        return

    remaining = (
        payment_request.amount
        - payment_request.fulfilled_amount
    )

    applied_amount = min(amount, remaining)

    payment_request.fulfilled_amount += applied_amount

    if payment_request.fulfilled_amount == payment_request.amount:
        payment_request.status = "fulfilled"
        payment_request.resolved_at = datetime.now(timezone.utc)

    db.flush()