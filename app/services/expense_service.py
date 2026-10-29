
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

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
) -> tuple[Expense, list[ExpenseSplit]]:

    # 1. Check that the group exists.
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

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

    if group is None:
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
            .where(Expense.group_id == group_id)
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

    if group is None:
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
