from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.payment import Payment

from app.schemas.payment import PaymentCreate

from app.services.ledger_service import calculate_group_balances
from app.services.payment_request_service import reconcile_payment_request

def create_payment(
    db: Session,
    group_id: int,
    sender_id: int,
    payload: PaymentCreate,
    idempotency_key: str | None = None,
) -> Payment:

    # 1. Verify that the group exists.
        # 1. Lock the group before creating a payment.
    # This serializes payment creation with other financial operations.
    group = db.scalar(
        select(Group)
        .where(Group.id == group_id)
        .with_for_update()
    )

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # 2. Retrieve the group's member IDs.
    member_ids = set(
        db.scalars(
            select(GroupMember.user_id).where(
                GroupMember.group_id == group_id
            )
        ).all()
    )

    # 3. Only group members can report payments.
    if sender_id not in member_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # 4. The recipient must also belong to the group.
    if payload.to_user_id not in member_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment recipient must be a group member",
        )

    # 5. A user cannot report a payment to themselves.
    if sender_id == payload.to_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot make a payment to yourself",
        )

        # 6. Check whether this payment request was already processed.
    if idempotency_key is not None:
        existing_payment = db.scalar(
            select(Payment).where(
                Payment.group_id == group_id,
                Payment.from_user_id == sender_id,
                Payment.idempotency_key == idempotency_key,
            )
        )

        if existing_payment is not None:
            # A key cannot be reused for different payment details.
            if (
                existing_payment.to_user_id != payload.to_user_id
                or existing_payment.amount != payload.amount
            ):
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different payment",
                )

            # Return the original payment without creating another.
            db.commit()
            return existing_payment

    if (
        group.currency == "JPY"
        and payload.amount != payload.amount.to_integral_value()
    ):
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="JPY amounts must be whole numbers",
        )

    # 6. Save the payment with pending status.
    try:
        payment = Payment(
            group_id=group_id,
            from_user_id=sender_id,
            to_user_id=payload.to_user_id,
            amount=payload.amount,
            status="pending",
            idempotency_key=idempotency_key,
        )

        db.add(payment)
        db.flush()
        db.commit()

        return payment

    except Exception:
        db.rollback()
        raise



def confirm_payment(
    db: Session,
    group_id: int,
    payment_id: int,
    recipient_id: int,
) -> Payment:

    try:
        # 1. Lock the group to coordinate financial operations.
        locked_group = db.scalar(
            select(Group)
            .where(Group.id == group_id)
            .with_for_update()
        )

        if locked_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found",
            )

        # 2. Find the payment in the requested group.
        payment = db.scalar(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.group_id == group_id,
            )
        )

        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        # 3. Only the intended recipient can confirm.
        if payment.to_user_id != recipient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient can confirm this payment",
            )

        # 4. Only pending payments can be confirmed.
        if payment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment is no longer pending",
            )

        # 5. Check outstanding balances before confirmation.
        balances = calculate_group_balances(
            db=db,
            group_id=group_id,
        )

        sender_balance = balances.get(
            payment.from_user_id,
            Decimal("0.00"),
        )

        recipient_balance = balances.get(
            payment.to_user_id,
            Decimal("0.00"),
        )

        # Sender must owe money.
        if sender_balance >= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sender has no outstanding debt",
            )

        # Recipient must be owed money.
        if recipient_balance <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recipient has no outstanding credit",
            )

        # 6. Calculate the maximum allowed payment.
        maximum_payment = min(
            -sender_balance,
            recipient_balance,
        )

        if payment.amount > maximum_payment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment exceeds outstanding balance",
            )

        # 7. Atomically change pending -> confirmed.
        result = db.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.group_id == group_id,
                Payment.to_user_id == recipient_id,
                Payment.status == "pending",
            )
            .values(
                status="confirmed",
                confirmed_at=func.now(),
            )
            .returning(
                Payment.status,
                Payment.confirmed_at,
            )
            .execution_options(synchronize_session=False)
        )

        updated = result.one_or_none()

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment was already processed",
            )

        payment.status = updated.status
        payment.confirmed_at = updated.confirmed_at

        reconcile_payment_request(
            db=db,
            group_id=group_id,
            sender_id=payment.from_user_id,
            recipient_id=payment.to_user_id,
            amount=payment.amount,
        )

        db.commit()

        return payment

    except Exception:
        db.rollback()
        raise



def reject_payment(
    db: Session,
    group_id: int,
    payment_id: int,
    recipient_id: int,
) -> Payment:

    try:
        # 1. Lock the group to coordinate financial operations.
        locked_group = db.scalar(
            select(Group)
            .where(Group.id == group_id)
            .with_for_update()
        )

        if locked_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found",
            )

        # 2. Find the payment in this group.
        payment = db.scalar(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.group_id == group_id,
            )
        )

        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        # 3. Only the recipient can reject the payment.
        if payment.to_user_id != recipient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient can reject this payment",
            )

        # 4. Only pending payments can be rejected.
        if payment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment is no longer pending",
            )

        # 5. Atomically update the payment status.
        result = db.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.group_id == group_id,
                Payment.to_user_id == recipient_id,
                Payment.status == "pending",
            )
            .values(status="rejected")
            .returning(
                Payment.status,
                Payment.confirmed_at,
            )
            .execution_options(synchronize_session=False)
        )

        updated = result.one_or_none()

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment was already processed",
            )

        payment.status = updated.status
        payment.confirmed_at = updated.confirmed_at

        db.commit()

        return payment

    except Exception:
        db.rollback()
        raise

def list_group_payments(
    db: Session,
    group_id: int,
    user_id: int,
) -> list[Payment]:
    # 1. Verify that the group exists.
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # 2. Verify that the requester belongs to this group.
    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # 3. Retrieve payments belonging to this group.
    # Newest payments appear first.
    payments = db.scalars(
        select(Payment)
        .where(Payment.group_id == group_id)
        .order_by(
            Payment.created_at.desc(),
            Payment.id.desc(),
        )
    ).all()

    return list(payments)
