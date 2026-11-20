
from decimal import Decimal

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit

from app.schemas.payment import PaymentCreate
from app.services.payment_service import (
    create_payment,
    confirm_payment,
    reject_payment,
)
from app.services.ledger_service import calculate_group_balances


def test_payment_reconciliation_lifecycle(db_session):
    # 1. Create Alice and Bob.
    alice = User(
        full_name="Alice Reconciliation",
        email="reconciliation_alice@example.com",
        hashed_password="test_hash",
    )
    bob = User(
        full_name="Bob Reconciliation",
        email="reconciliation_bob@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob])
    db_session.flush()

    # 2. Create a group.
    group = Group(
        name="Reconciliation Test Group",
        created_by=alice.id,
    )
    db_session.add(group)
    db_session.flush()

    db_session.add_all([
        GroupMember(
            group_id=group.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group.id,
            user_id=bob.id,
            role="member",
        ),
    ])
    db_session.flush()

    # 3. Alice pays $100, split equally.
    expense = Expense(
        group_id=group.id,
        paid_by=alice.id,
        description="Groceries",
        amount=Decimal("100.00"),
    )
    db_session.add(expense)
    db_session.flush()

    db_session.add_all([
        ExpenseSplit(
            expense_id=expense.id,
            user_id=alice.id,
            amount_owed=Decimal("50.00"),
        ),
        ExpenseSplit(
            expense_id=expense.id,
            user_id=bob.id,
            amount_owed=Decimal("50.00"),
        ),
    ])
    db_session.flush()

    # 4. Verify initial balances.
    balances = calculate_group_balances(db_session, group.id)

    assert balances[alice.id] == Decimal("50.00")
    assert balances[bob.id] == Decimal("-50.00")

    # 5. Bob reports paying Alice $30.
    payment = create_payment(
        db=db_session,
        group_id=group.id,
        sender_id=bob.id,
        payload=PaymentCreate(
            to_user_id=alice.id,
            amount=Decimal("30.00"),
        ),
    )

    # Pending payments must not affect balances.
    balances = calculate_group_balances(db_session, group.id)

    assert balances[alice.id] == Decimal("50.00")
    assert balances[bob.id] == Decimal("-50.00")

    # 6. Alice confirms the payment.
    confirm_payment(
        db=db_session,
        group_id=group.id,
        payment_id=payment.id,
        recipient_id=alice.id,
    )

    balances = calculate_group_balances(db_session, group.id)

    assert balances[alice.id] == Decimal("20.00")
    assert balances[bob.id] == Decimal("-20.00")
    assert sum(balances.values()) == Decimal("0.00")

    # 7. Bob reports another payment.
    second_payment = create_payment(
        db=db_session,
        group_id=group.id,
        sender_id=bob.id,
        payload=PaymentCreate(
            to_user_id=alice.id,
            amount=Decimal("10.00"),
        ),
    )

    # Alice rejects it.
    reject_payment(
        db=db_session,
        group_id=group.id,
        payment_id=second_payment.id,
        recipient_id=alice.id,
    )

    # Rejected payments must not affect balances.
    balances = calculate_group_balances(db_session, group.id)

    assert balances[alice.id] == Decimal("20.00")
    assert balances[bob.id] == Decimal("-20.00")
    assert sum(balances.values()) == Decimal("0.00")
