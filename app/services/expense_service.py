
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.services.group_service import require_active_group
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.schemas.expense import ExpenseCreate


def create_expense(
    db: Session,
    group_id: int,
    payer_id: int,
    payload: ExpenseCreate,
    idempotency_key: str | None = None,
) -> tuple[Expense, list[ExpenseSplit]]:

# 1. Lock the group before changing its financial ledger.
# This coordinates expense creation with payment confirmation.
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

    require_active_group(group)
    # 2. Only group members can record expenses.
    member_ids = set(
        db.scalars(
            select(GroupMember.user_id).where(
                GroupMember.group_id == group_id
            )
        ).all()
    )

    if payer_id not in member_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # CHANGE B — Check whether this expense already exists.
    if idempotency_key is not None:
        existing_expense = db.scalar(
            select(Expense).where(
                Expense.group_id == group_id,
                Expense.paid_by == payer_id,
                Expense.idempotency_key == idempotency_key,
            )
        )

        if existing_expense is not None:
            if existing_expense.voided_at is not None:
                raise HTTPException(
                    status_code=409,
                    detail="This expense was previously deleted",
                )
            existing_splits = list(
                db.scalars(
                    select(ExpenseSplit)
                    .where(ExpenseSplit.expense_id == existing_expense.id)
                    .order_by(ExpenseSplit.id)
                ).all()
            )

            requested_splits = {
                split.user_id: split.amount_owed
                for split in payload.splits
            }

            saved_splits = {
                split.user_id: split.amount_owed
                for split in existing_splits
            }

            if (
                existing_expense.description != payload.description.strip()
                or existing_expense.amount != payload.amount
                or existing_expense.category != payload.category
                or existing_expense.expense_date != payload.expense_date
                or existing_expense.reference != payload.reference
                or existing_expense.split_method != payload.split_method
                or saved_splits != requested_splits
                or len(payload.splits) != len(requested_splits)
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different expense",
                )

            db.commit()
            return existing_expense, existing_splits

    if group.currency == "JPY":
        amounts = [payload.amount, *(split.amount_owed for split in payload.splits)]
        if any(amount != amount.to_integral_value() for amount in amounts):
            db.rollback()
            raise HTTPException(
                status_code=422,
                detail="JPY amounts must be whole numbers",
            )

    # 3. Prevent duplicate participants.
    split_user_ids = [
        split.user_id for split in payload.splits
    ]

    if len(split_user_ids) != len(set(split_user_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate users in expense splits",
        )

    # 4. Every participant must belong to the group.
    if not set(split_user_ids).issubset(member_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All expense participants must be group members",
        )

    # 5. Shares must add up to the expense total.
    total_splits = sum(
        (split.amount_owed for split in payload.splits),
        Decimal("0.00"),
    )

    if total_splits != payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense splits must equal the total amount",
        )

    # 6. Save the expense and splits atomically.
    try:
        expense = Expense(
            group_id=group_id,
            paid_by=payer_id,
            description=payload.description.strip(),
            amount=payload.amount,
            category=payload.category,
            expense_date=payload.expense_date,
            reference=payload.reference,
            split_method=payload.split_method,
            idempotency_key=idempotency_key,
        )

        if not expense.description:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expense description cannot be blank",
            )

        db.add(expense)
        db.flush()

        splits = [
            ExpenseSplit(
                expense_id=expense.id,
                user_id=split.user_id,
                amount_owed=split.amount_owed,
            )
            for split in payload.splits
        ]

        db.add_all(splits)
        db.flush()

        db.commit()

        db.refresh(expense)

        for split in splits:
            db.refresh(split)

        return expense, splits

    except Exception:
        db.rollback()
        raise

def get_group_expenses(
    db: Session,
    group_id: int,
    requester_id: int,
) -> list[tuple[Expense, list[ExpenseSplit]]]:

    # Verify the group exists.
    group = db.get(Group, group_id)

    if group is None or group.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail="Group not found",
        )

    # Verify the requester belongs to the group.
    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == requester_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    # Query 1: Fetch all expenses in the group.
    expenses = list(
        db.scalars(
            select(Expense)
            .where(Expense.group_id == group_id,Expense.voided_at.is_(None),)
            .order_by(
                Expense.created_at.desc(),
                Expense.id.desc(),
            )
        ).all()
    )

    if not expenses:
        return []

    # Collect all expense IDs.
    expense_ids = [expense.id for expense in expenses]

    # Query 2: Fetch all associated splits at once.
    splits = db.scalars(
        select(ExpenseSplit)
        .where(ExpenseSplit.expense_id.in_(expense_ids))
        .order_by(ExpenseSplit.id)
    ).all()

    # Organize splits by expense ID.
    splits_by_expense = {
        expense_id: []
        for expense_id in expense_ids
    }

    for split in splits:
        splits_by_expense[split.expense_id].append(split)

    # Return expenses with their corresponding splits.
    return [
        (expense, splits_by_expense[expense.id])
        for expense in expenses
    ]




def get_expense_details(
    db: Session,
    group_id: int,
    expense_id: int,
    requester_id: int,
) -> tuple[Expense, list[ExpenseSplit]]:

    # 1. Verify that the group exists.
    group = db.get(Group, group_id)

    if group is None or group.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # 2. Verify that the requester belongs to the group.
    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == requester_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # 3. Retrieve the requested expense.
    expense = db.scalar(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.group_id == group_id,
            Expense.voided_at.is_(None),
        )
    )

    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    # 4. Retrieve the expense's participant shares.
    splits = db.scalars(
        select(ExpenseSplit)
        .where(ExpenseSplit.expense_id == expense_id)
        .order_by(ExpenseSplit.id)
    ).all()

    return expense, list(splits)

from app.schemas.expense import ExpenseUpdate
from app.services.group_service import lock_group

def update_expense(db: Session, group_id: int, expense_id: int, requester_id: int, payload: ExpenseUpdate):
    try:
        group = lock_group(db, group_id)
        require_active_group(group)
        expense, splits = get_expense_details(db, group_id, expense_id, requester_id)
        if expense.paid_by != requester_id:
            raise HTTPException(status_code=403, detail="Only the payer can edit this expense")
        expense.description = payload.description
        expense.category = payload.category
        expense.expense_date = payload.expense_date
        expense.reference = payload.reference or None
        db.flush()
        db.commit()
        return expense, splits
    except Exception:
        db.rollback()
        raise
