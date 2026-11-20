
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.group_member import GroupMember
from app.models.payment import Payment


def calculate_group_balances(
    db: Session,
    group_id: int,
) -> dict[int, Decimal]:
    """
    Calculate each group member's net balance.

    Positive: member should receive money.
    Negative: member owes money.
    Zero: member is settled.

    Only confirmed payments affect balances.
    """

    # Step 1: Retrieve group members.
    member_ids = db.scalars(
        select(GroupMember.user_id).where(
            GroupMember.group_id == group_id
        )
    ).all()

    balances = {
        member_id: Decimal("0.00")
        for member_id in member_ids
    }

    # Step 2: Retrieve expenses.
    expenses = db.scalars(
        select(Expense).where(
            Expense.group_id == group_id
        )
    ).all()

    # Step 3: Credit expense payers.
    for expense in expenses:
        balances[expense.paid_by] += expense.amount

    # Step 4: Subtract expense shares.
    if expenses:
        expense_ids = [expense.id for expense in expenses]

        splits = db.scalars(
            select(ExpenseSplit).where(
                ExpenseSplit.expense_id.in_(expense_ids)
            )
        ).all()

        for split in splits:
            balances[split.user_id] -= split.amount_owed

    # Step 5: Retrieve confirmed payments only.
    confirmed_payments = db.scalars(
        select(Payment).where(
            Payment.group_id == group_id,
            Payment.status == "confirmed",
        )
    ).all()

    # Step 6: Apply confirmed payment adjustments.
    for payment in confirmed_payments:
        # Sender has paid money, so their debt decreases.
        balances[payment.from_user_id] += payment.amount

        # Recipient has received money, so their credit decreases.
        balances[payment.to_user_id] -= payment.amount

    return balances
