
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from decimal import Decimal
from threading import Event
from uuid import uuid4

from sqlalchemy import select, func, text

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.schemas.expense import ExpenseCreate
from app.services.expense_service import create_expense

from tests.conftest import TestingSessionLocal, test_engine


def test_concurrent_expense_retries_create_only_one_expense():
    # Verify that we are using the isolated test database.
    with test_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    assert database_name == "ledgersplit_test_db"

    unique_id = uuid4().hex
    user_id = None
    group_id = None

    try:
        # 1. Create committed records visible to both threads.
        with TestingSessionLocal() as db:
            user = User(
                full_name="Concurrent Retry User",
                email=f"concurrent_retry_{unique_id}@example.com",
                hashed_password="test_hash",
            )
            db.add(user)
            db.flush()
            user_id = user.id

            group = Group(
                name="Concurrent Idempotency Group",
                created_by=user_id,
            )
            db.add(group)
            db.flush()
            group_id = group.id

            db.add(
                GroupMember(
                    group_id=group_id,
                    user_id=user_id,
                    role="owner",
                )
            )

            db.commit()

        # 2. Both workers will submit the same expense.
        payload = ExpenseCreate(
            description="Concurrent groceries",
            amount=Decimal("100.00"),
            splits=[
                {
                    "user_id": user_id,
                    "amount_owed": Decimal("100.00"),
                }
            ],
        )

        idempotency_key = f"concurrent-expense-{unique_id}"

        lock_acquired = Event()
        release_lock = Event()
        second_started = Event()

        def first_worker():
            with TestingSessionLocal() as db:
                # Acquire the group lock before the second worker.
                db.execute(
                    select(Group)
                    .where(Group.id == group_id)
                    .with_for_update()
                ).scalar_one()

                lock_acquired.set()

                if not release_lock.wait(timeout=10):
                    raise TimeoutError("First worker release timed out")

                expense, _ = create_expense(
                    db=db,
                    group_id=group_id,
                    payer_id=user_id,
                    payload=payload,
                    idempotency_key=idempotency_key,
                )

                return expense.id

        def second_worker():
            with TestingSessionLocal() as db:
                second_started.set()

                expense, _ = create_expense(
                    db=db,
                    group_id=group_id,
                    payer_id=user_id,
                    payload=payload,
                    idempotency_key=idempotency_key,
                )

                return expense.id

        # 3. Execute the workers using independent sessions.
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(first_worker)

            assert lock_acquired.wait(timeout=10)

            second_future = executor.submit(second_worker)

            try:
                assert second_started.wait(timeout=10)

                # Worker B must not finish while A holds the lock.
                try:
                    second_future.result(timeout=0.3)
                except FutureTimeout:
                    pass
                else:
                    raise AssertionError(
                        "Second expense request bypassed the group lock"
                    )

            finally:
                release_lock.set()

            first_expense_id = first_future.result(timeout=20)
            second_expense_id = second_future.result(timeout=20)

        # 4. Both requests must resolve to the same expense.
        assert first_expense_id == second_expense_id

        # 5. Verify exactly one persisted expense and split.
        with TestingSessionLocal() as db:
            expense_count = db.scalar(
                select(func.count())
                .select_from(Expense)
                .where(
                    Expense.group_id == group_id,
                    Expense.idempotency_key == idempotency_key,
                )
            )

            split_count = db.scalar(
                select(func.count())
                .select_from(ExpenseSplit)
                .where(
                    ExpenseSplit.expense_id == first_expense_id
                )
            )

            assert expense_count == 1
            assert split_count == 1

    finally:
        # 6. Clean up the committed test records.
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

                for expense in expenses:
                    db.delete(expense)

                db.flush()

                members = db.scalars(
                    select(GroupMember).where(
                        GroupMember.group_id == group_id
                    )
                ).all()

                for member in members:
                    db.delete(member)

                db.flush()

                group = db.get(Group, group_id)
                if group is not None:
                    db.delete(group)

                db.flush()

                if user_id is not None:
                    user = db.get(User, user_id)
                    if user is not None:
                        db.delete(user)

                db.commit()
