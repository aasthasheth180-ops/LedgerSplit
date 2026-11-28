from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.expense import Expense
from app.models.payment import Payment
from app.models.payment_request import PaymentRequest
from app.services.group_service import (
    lock_group,
    get_membership,
    require_active_group,
)
from app.services.ledger_service import calculate_group_balances

def require_owner(
    db: Session,
    group_id: int,
    user_id: int,
) -> None:
    membership = get_membership(db, group_id, user_id)

    if membership is None or membership.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only the group owner can perform this action",
        )


def has_financial_history(
    db: Session,
    group_id: int,
) -> bool:
    for model in (Expense, Payment, PaymentRequest):
        record = db.scalar(
            select(model.id)
            .where(model.group_id == group_id)
            .limit(1)
        )

        if record is not None:
            return True

    return False


def delete_group(
    db: Session,
    group_id: int,
    requester_id: int,
) -> None:
    try:
        group = lock_group(db, group_id)
        require_owner(db, group_id, requester_id)

        if group.deleted_at is not None:
            db.commit()
            return

        if has_financial_history(db, group_id):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Groups with financial history cannot "
                    "be deleted. Archive the group instead."
                ),
            )

        group.deleted_at = datetime.now(timezone.utc)

        db.commit()

    except Exception:
        db.rollback()
        raise


def archive_group(
    db: Session,
    group_id: int,
    requester_id: int,
) -> Group:
    try:
        group = lock_group(db, group_id)
        require_owner(db, group_id, requester_id)

        if group.deleted_at is not None:
            raise HTTPException(
                status_code=404,
                detail="Group not found",
            )

        if group.archived_at is not None:
            db.commit()
            return group

        balances = calculate_group_balances(db, group_id)

        if any(balance != 0 for balance in balances.values()):
            raise HTTPException(
                status_code=409,
                detail="Settle all balances before archiving",
            )

        for model in (Payment, PaymentRequest):
            pending = db.scalar(
                select(model.id)
                .where(
                    model.group_id == group_id,
                    model.status == "pending",
                )
                .limit(1)
            )

            if pending is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Resolve pending payments and requests first",
                )

        group.archived_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(group)

        return group

    except Exception:
        db.rollback()
        raise


def void_expense(
    db: Session,
    group_id: int,
    expense_id: int,
    requester_id: int,
) -> None:
    try:
        group = lock_group(db, group_id)
        require_active_group(group)

        membership = get_membership(
            db, group_id, requester_id
        )

        if membership is None:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this group",
            )

        expense = db.scalar(
            select(Expense).where(
                Expense.id == expense_id,
                Expense.group_id == group_id,
            )
        )

        if expense is None:
            raise HTTPException(
                status_code=404,
                detail="Expense not found",
            )

        if expense.paid_by != requester_id:
            raise HTTPException(
                status_code=403,
                detail="Only the original payer can delete this expense",
            )

        if expense.voided_at is not None:
            db.commit()
            return

        for model in (Payment, PaymentRequest):
            record = db.scalar(
                select(model.id)
                .where(model.group_id == group_id)
                .limit(1)
            )

            if record is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Expense deletion is unavailable in "
                        "groups with payment or request history"
                    ),
                )

        expense.voided_at = datetime.now(timezone.utc)

        db.commit()

    except Exception:
        db.rollback()
        raise