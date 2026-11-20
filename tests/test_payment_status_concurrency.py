
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.payment import Payment

from app.services.payment_service import confirm_payment, reject_payment
from tests.conftest import TestingSessionLocal, test_engine


def test_simultaneous_confirm_and_reject_only_one_succeeds():

    # Ensure we're using the dedicated test database.
    with test_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    assert database_name == "ledgersplit_test_db"

    unique_id = uuid4().hex

    alice_id = None
    bob_id = None
    group_id = None
    payment_id = None

    try:
        with TestingSessionLocal() as db:

            # Create Alice and Bob.
            alice = User(
                full_name="Status Alice",
                email=f"status_alice_{unique_id}@example.com",
                hashed_password="test_hash",
            )

            bob = User(
                full_name="Status Bob",
                email=f"status_bob_{unique_id}@example.com",
                hashed_password="test_hash",
            )

            db.add_all([alice, bob])
            db.flush()

            alice_id = alice.id
            bob_id = bob.id

            # Create their group.
            group = Group(
                name="Payment Status Concurrency Group",
                created_by=alice_id,
            )

            db.add(group)
            db.flush()

            group_id = group.id

            # Add both users to the group.
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

            # Alice pays $100 for groceries.
            expense = Expense(
                group_id=group_id,
                paid_by=alice_id,
                description="Groceries",
                amount=Decimal("100.00"),
            )

            db.add(expense)
            db.flush()

            # Alice and Bob each owe $50.
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

            # Bob reports paying Alice $30.
            payment = Payment(
                group_id=group_id,
                from_user_id=bob_id,
                to_user_id=alice_id,
                amount=Decimal("30.00"),
                status="pending",
            )

            db.add(payment)
            db.flush()

            payment_id = payment.id

            # Make records visible to both future threads.
            db.commit()
# Start both operations at approximately the same time.
        barrier = Barrier(2, timeout=10)

        def process_payment(action):
            with TestingSessionLocal() as db:
                barrier.wait()

                try:
                    if action == "confirm":
                        confirm_payment(
                            db=db,
                            group_id=group_id,
                            payment_id=payment_id,
                            recipient_id=alice_id,
                        )
                    else:
                        reject_payment(
                            db=db,
                            group_id=group_id,
                            payment_id=payment_id,
                            recipient_id=alice_id,
                        )

                    return 200

                except HTTPException as exc:
                    db.rollback()
                    return exc.status_code

        # Execute confirmation and rejection concurrently.
        with ThreadPoolExecutor(max_workers=2) as executor:
            confirm_future = executor.submit(
                process_payment, "confirm"
            )
            reject_future = executor.submit(
                process_payment, "reject"
            )

            results = [
                confirm_future.result(timeout=20),
                reject_future.result(timeout=20),
            ]

        # Exactly one operation must succeed.
        assert sorted(results) == [200, 409]

        # Verify the final database state.
        with TestingSessionLocal() as db:
            saved_payment = db.get(Payment, payment_id)

            assert saved_payment.status in ("confirmed", "rejected")

            if saved_payment.status == "confirmed":
                assert saved_payment.confirmed_at is not None
            else:
                assert saved_payment.confirmed_at is None

    finally:
        # Remove the records created by this test.
        if group_id is not None:
            with TestingSessionLocal() as db:
                expenses = db.scalars(
                    select(Expense).where(
                        Expense.group_id == group_id
                    )
                ).all()

                for expense in expenses:
                    splits = db.scalars(
                        select(ExpenseSplit).where(
                            ExpenseSplit.expense_id == expense.id
                        )
                    ).all()

                    for split in splits:
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
