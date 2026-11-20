
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.payment import Payment

from app.services.ledger_service import calculate_group_balances
from app.services.payment_service import confirm_payment

from tests.conftest import TestingSessionLocal, test_engine


def test_simultaneous_confirmations_prevent_overpayment():
    # This test commits data, unlike the usual rollback fixture.
    # Use only the dedicated PostgreSQL test database.
    with test_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    assert database_name == "ledgersplit_test_db"

    unique_id = uuid4().hex
    alice_id = None
    bob_id = None
    group_id = None

    try:
        # Prepare committed test data.
        with TestingSessionLocal() as db:
            alice = User(
                full_name="Concurrency Alice",
                email=f"concurrency_alice_{unique_id}@example.com",
                hashed_password="test_hash",
            )
            bob = User(
                full_name="Concurrency Bob",
                email=f"concurrency_bob_{unique_id}@example.com",
                hashed_password="test_hash",
            )

            db.add_all([alice, bob])
            db.flush()

            alice_id = alice.id
            bob_id = bob.id

            group = Group(
                name="Concurrency Test Group",
                created_by=alice_id,
            )
            db.add(group)
            db.flush()
            group_id = group.id

            db.add_all([
                GroupMember(
                    group_id=group_id,
                    user_id=alice_id,
                    role="owner",
                ),
                GroupMember(
                    group_id=group_id,
                    user_id=bob_id,
                    role="member",
                ),
            ])

            expense = Expense(
                group_id=group_id,
                paid_by=alice_id,
                description="Groceries",
                amount=Decimal("100.00"),
            )
            db.add(expense)
            db.flush()

            db.add_all([
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=alice_id,
                    amount_owed=Decimal("50.00"),
                ),
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=bob_id,
                    amount_owed=Decimal("50.00"),
                ),
            ])

            payments = [
                Payment(
                    group_id=group_id,
                    from_user_id=bob_id,
                    to_user_id=alice_id,
                    amount=Decimal("40.00"),
                    status="pending",
                )
                for _ in range(2)
            ]

            db.add_all(payments)
            db.flush()

            payment_ids = [payment.id for payment in payments]
            db.commit()

        # Both workers wait here before attempting confirmation.
        barrier = Barrier(2, timeout=10)

        def confirm_in_separate_session(payment_id):
            with TestingSessionLocal() as db:
                barrier.wait()

                try:
                    confirm_payment(
                        db=db,
                        group_id=group_id,
                        payment_id=payment_id,
                        recipient_id=alice_id,
                    )
                    return 200

                except HTTPException as exc:
                    db.rollback()
                    return exc.status_code

        # Start two independent database transactions.
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    confirm_in_separate_session,
                    payment_id,
                )
                for payment_id in payment_ids
            ]

            results = [
                future.result(timeout=20)
                for future in futures
            ]

        # Exactly one confirmation should succeed.
        assert sorted(results) == [200, 409]

        # Verify persisted payment statuses and balances.
        with TestingSessionLocal() as db:
            saved_payments = db.scalars(
                select(Payment).where(
                    Payment.id.in_(payment_ids)
                )
            ).all()

            assert sum(
                payment.status == "confirmed"
                for payment in saved_payments
            ) == 1

            assert sum(
                payment.status == "pending"
                for payment in saved_payments
            ) == 1

            balances = calculate_group_balances(
                db=db,
                group_id=group_id,
            )

            assert balances[alice_id] == Decimal("10.00")
            assert balances[bob_id] == Decimal("-10.00")

    finally:
        # Remove only records created by this test.
        # Delete children before their parent records.
        if group_id is not None:
            with TestingSessionLocal() as db:
                expenses = db.scalars(
                    select(Expense).where(
                        Expense.group_id == group_id
                    )
                ).all()

                for expense in expenses:
                    for split in db.scalars(
                        select(ExpenseSplit).where(
                            ExpenseSplit.expense_id == expense.id
                        )
                    ).all():
                        db.delete(split)

                db.flush()

                for payment in db.scalars(
                    select(Payment).where(
                        Payment.group_id == group_id
                    )
                ).all():
                    db.delete(payment)

                for expense in expenses:
                    db.delete(expense)

                for member in db.scalars(
                    select(GroupMember).where(
                        GroupMember.group_id == group_id
                    )
                ).all():
                    db.delete(member)

                db.flush()

                group = db.get(Group, group_id)
                if group is not None:
                    db.delete(group)

                db.flush()

                for user_id in (alice_id, bob_id):
                    if user_id is not None:
                        user = db.get(User, user_id)
                        if user is not None:
                            db.delete(user)

                db.commit()
