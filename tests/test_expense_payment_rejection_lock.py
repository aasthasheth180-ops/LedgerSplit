
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from uuid import uuid4

from sqlalchemy import select, text

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.payment import Payment

from app.schemas.expense import ExpenseCreate
from app.services.expense_service import create_expense
from app.services.payment_service import reject_payment
from app.services.ledger_service import calculate_group_balances

from tests.conftest import TestingSessionLocal, test_engine


def test_payment_rejection_waits_for_group_lock():
    # This test uses committed records and independent sessions.
    # Never run it against the application database.
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
        # 1. Prepare initial financial records.
        with TestingSessionLocal() as db:
            alice = User(
                full_name="Expense Lock Alice",
                email=f"expense_lock_alice_{unique_id}@example.com",
                hashed_password="test_hash",
            )
            bob = User(
                full_name="Expense Lock Bob",
                email=f"expense_lock_bob_{unique_id}@example.com",
                hashed_password="test_hash",
            )

            db.add_all([alice, bob])
            db.flush()

            alice_id = alice.id
            bob_id = bob.id

            group = Group(
                name="Expense Payment Lock Test",
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
                description="Initial groceries",
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
            db.commit()

        # 2. Coordinate the worker threads.
        lock_acquired = Event()
        release_lock = Event()
        confirmation_started = Event()

        def create_expense_worker():
            with TestingSessionLocal() as db:
                # Hold the group lock before expense creation.
                db.execute(
                    select(Group)
                    .where(Group.id == group_id)
                    .with_for_update()
                ).scalar_one()

                lock_acquired.set()

                if not release_lock.wait(timeout=10):
                    raise TimeoutError("Expense worker release timed out")

                payload = ExpenseCreate(
                    description="Additional groceries",
                    amount=Decimal("20.00"),
                    splits=[
                        {
                            "user_id": alice_id,
                            "amount_owed": Decimal("10.00"),
                        },
                        {
                            "user_id": bob_id,
                            "amount_owed": Decimal("10.00"),
                        },
                    ],
                )

                create_expense(
                    db=db,
                    group_id=group_id,
                    payer_id=alice_id,
                    payload=payload,
                )

        def reject_payment_worker():
            with TestingSessionLocal() as db:
                confirmation_started.set()

                reject_payment(
                    db=db,
                    group_id=group_id,
                    payment_id=payment_id,
                    recipient_id=alice_id,
                )

        # 3. Run the two operations with independent sessions.
        with ThreadPoolExecutor(max_workers=2) as executor:
            expense_future = executor.submit(create_expense_worker)

            assert lock_acquired.wait(timeout=10)

            payment_future = executor.submit(reject_payment_worker)

            try:
                assert confirmation_started.wait(timeout=10)

                # The payment must not complete while the group
                # lock is held by the expense worker.
                from concurrent.futures import TimeoutError as FutureTimeout

                try:
                    payment_future.result(timeout=0.3)
                except FutureTimeout:
                    pass
                else:
                    raise AssertionError(
                        "Payment confirmation bypassed the group lock"
                    )

            finally:
                # Always release the worker, even if an assertion fails.
                release_lock.set()

            expense_future.result(timeout=20)
            payment_future.result(timeout=20)

        # 4. Verify final persisted records and ledger balances.
        with TestingSessionLocal() as db:
            saved_payment = db.get(Payment, payment_id)

            assert saved_payment.status == "rejected"
            assert saved_payment.confirmed_at is None

            expenses = db.scalars(
                select(Expense).where(
                    Expense.group_id == group_id
                )
            ).all()

            assert len(expenses) == 2

            balances = calculate_group_balances(
                db=db,
                group_id=group_id,
            )

            assert balances[alice_id] == Decimal("60.00")
            assert balances[bob_id] == Decimal("-60.00")

    finally:
        # 5. Clean up only this test's committed records.
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
