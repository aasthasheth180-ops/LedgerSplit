
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from decimal import Decimal
from threading import Event
from uuid import uuid4

from sqlalchemy import select, func, text

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.payment import Payment

from app.schemas.payment import PaymentCreate
from app.services.payment_service import create_payment

from tests.conftest import TestingSessionLocal, test_engine


def test_concurrent_payment_retries_create_only_one_payment():
    # This test commits data and uses independent DB sessions.
    # Never run against the application database.
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
        # 1. Prepare committed users and group membership.
        with TestingSessionLocal() as db:
            alice = User(
                full_name="Payment Retry Alice",
                email=f"payment_retry_alice_{unique_id}@example.com",
                hashed_password="test_hash",
            )
            bob = User(
                full_name="Payment Retry Bob",
                email=f"payment_retry_bob_{unique_id}@example.com",
                hashed_password="test_hash",
            )

            db.add_all([alice, bob])
            db.flush()

            alice_id = alice.id
            bob_id = bob.id

            group = Group(
                name="Payment Idempotency Concurrency Group",
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

            db.commit()

        # 2. Both workers use the same payment details and key.
        payload = PaymentCreate(
            to_user_id=alice_id,
            amount=Decimal("30.00"),
        )

        idempotency_key = f"payment-retry-{unique_id}"

        lock_acquired = Event()
        release_lock = Event()
        second_started = Event()

        def first_worker():
            with TestingSessionLocal() as db:
                # Hold the group lock before the second worker.
                db.execute(
                    select(Group)
                    .where(Group.id == group_id)
                    .with_for_update()
                ).scalar_one()

                lock_acquired.set()

                if not release_lock.wait(timeout=10):
                    raise TimeoutError("First worker release timed out")

                payment = create_payment(
                    db=db,
                    group_id=group_id,
                    sender_id=bob_id,
                    payload=payload,
                    idempotency_key=idempotency_key,
                )

                return payment.id

        def second_worker():
            with TestingSessionLocal() as db:
                second_started.set()

                payment = create_payment(
                    db=db,
                    group_id=group_id,
                    sender_id=bob_id,
                    payload=payload,
                    idempotency_key=idempotency_key,
                )

                return payment.id

        # 3. Run the workers with separate sessions.
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(first_worker)

            assert lock_acquired.wait(timeout=10)

            second_future = executor.submit(second_worker)

            try:
                assert second_started.wait(timeout=10)

                # Worker B must wait while A holds the group lock.
                try:
                    second_future.result(timeout=0.3)
                except FutureTimeout:
                    pass
                else:
                    raise AssertionError(
                        "Second payment request bypassed the group lock"
                    )

            finally:
                release_lock.set()

            first_payment_id = first_future.result(timeout=20)
            second_payment_id = second_future.result(timeout=20)

        # 4. Both requests must return the same payment.
        assert first_payment_id == second_payment_id

        # 5. Verify only one payment was saved.
        with TestingSessionLocal() as db:
            payment_count = db.scalar(
                select(func.count())
                .select_from(Payment)
                .where(
                    Payment.group_id == group_id,
                    Payment.idempotency_key == idempotency_key,
                )
            )

            assert payment_count == 1

            saved_payment = db.get(Payment, first_payment_id)

            assert saved_payment is not None
            assert saved_payment.from_user_id == bob_id
            assert saved_payment.to_user_id == alice_id
            assert saved_payment.amount == Decimal("30.00")
            assert saved_payment.status == "pending"

    finally:
        # 6. Clean up only this test's committed records.
        if group_id is not None:
            with TestingSessionLocal() as db:
                payments = db.scalars(
                    select(Payment).where(
                        Payment.group_id == group_id
                    )
                ).all()

                for payment in payments:
                    db.delete(payment)

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

                for user_id in (alice_id, bob_id):
                    if user_id is not None:
                        user = db.get(User, user_id)

                        if user is not None:
                            db.delete(user)

                db.commit()
