
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.services.payment_service import (
    create_payment,
    confirm_payment,
    reject_payment,
)

from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit


@pytest.fixture
def payment_setup(db_session):
    # Create three test users.
    alice = User(
        full_name="Alice Payment",
        email="alice_payment@example.com",
        hashed_password="test_hash",
    )

    bob = User(
        full_name="Bob Payment",
        email="bob_payment@example.com",
        hashed_password="test_hash",
    )

    outsider = User(
        full_name="Payment Outsider",
        email="outsider_payment@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob, outsider])
    db_session.flush()

    # Alice creates a group.
    group = Group(
        name="Payment Test Group",
        created_by=alice.id,
    )

    db_session.add(group)
    db_session.flush()

    # Alice and Bob are group members.
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


    # Alice pays $100 for groceries.
    expense = Expense(
        group_id=group.id,
        paid_by=alice.id,
        description="Groceries",
        amount=Decimal("100.00"),
    )

    db_session.add(expense)
    db_session.flush()

    # Alice and Bob each owe $50.
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


    return {
        "group_id": group.id,
        "alice_id": alice.id,
        "bob_id": bob.id,
        "outsider_id": outsider.id,
    }


def test_create_payment_successfully(db_session, payment_setup):
    data = payment_setup

    payload = PaymentCreate(
        to_user_id=data["alice_id"],
        amount=Decimal("30.00"),
    )

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=payload,
    )

    assert payment.id is not None
    assert payment.group_id == data["group_id"]
    assert payment.from_user_id == data["bob_id"]
    assert payment.to_user_id == data["alice_id"]
    assert payment.amount == Decimal("30.00")
    assert payment.status == "pending"
    assert payment.confirmed_at is None

    # Verify the payment was persisted.
    saved_payment = db_session.get(Payment, payment.id)

    assert saved_payment is not None
    assert saved_payment.status == "pending"


def test_payment_group_not_found(db_session, payment_setup):
    data = payment_setup

    payload = PaymentCreate(
        to_user_id=data["alice_id"],
        amount="30.00",
    )

    with pytest.raises(HTTPException) as exc:
        create_payment(
            db=db_session,
            group_id=999999,
            sender_id=data["bob_id"],
            payload=payload,
        )

    assert exc.value.status_code == 404


def test_nonmember_cannot_report_payment(db_session, payment_setup):
    data = payment_setup

    payload = PaymentCreate(
        to_user_id=data["alice_id"],
        amount="30.00",
    )

    with pytest.raises(HTTPException) as exc:
        create_payment(
            db=db_session,
            group_id=data["group_id"],
            sender_id=data["outsider_id"],
            payload=payload,
        )

    assert exc.value.status_code == 403


def test_recipient_must_be_group_member(db_session, payment_setup):
    data = payment_setup

    payload = PaymentCreate(
        to_user_id=data["outsider_id"],
        amount="30.00",
    )

    with pytest.raises(HTTPException) as exc:
        create_payment(
            db=db_session,
            group_id=data["group_id"],
            sender_id=data["bob_id"],
            payload=payload,
        )

    assert exc.value.status_code == 400


def test_cannot_report_payment_to_self(db_session, payment_setup):
    data = payment_setup

    payload = PaymentCreate(
        to_user_id=data["bob_id"],
        amount="30.00",
    )

    with pytest.raises(HTTPException) as exc:
        create_payment(
            db=db_session,
            group_id=data["group_id"],
            sender_id=data["bob_id"],
            payload=payload,
        )

    assert exc.value.status_code == 400


def test_payment_amount_must_be_positive():
    with pytest.raises(ValidationError):
        PaymentCreate(
            to_user_id=1,
            amount=Decimal("-10.00"),
        )



def test_recipient_can_confirm_payment(db_session, payment_setup):
    data = payment_setup

    # Bob reports paying Alice $30.
    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    assert payment.status == "pending"

    # Alice confirms receiving the payment.
    confirmed = confirm_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=payment.id,
        recipient_id=data["alice_id"],
    )

    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_at is not None

    # Verify the updated state in PostgreSQL.
    db_session.expire_all()
    saved = db_session.get(Payment, payment.id)

    assert saved.status == "confirmed"
    assert saved.confirmed_at is not None


def test_sender_cannot_confirm_own_payment(db_session, payment_setup):
    data = payment_setup

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # Bob is the sender, not the recipient.
    with pytest.raises(HTTPException) as exc:
        confirm_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["bob_id"],
        )

    assert exc.value.status_code == 403
    assert payment.status == "pending"


def test_payment_cannot_be_confirmed_twice(db_session, payment_setup):
    data = payment_setup

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # First confirmation succeeds.
    confirm_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=payment.id,
        recipient_id=data["alice_id"],
    )

    # Second confirmation must fail.
    with pytest.raises(HTTPException) as exc:
        confirm_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["alice_id"],
        )

    assert exc.value.status_code == 409
    # A failed confirmation must end its database transaction.
    assert not db_session.in_transaction()



def test_recipient_can_reject_payment(db_session, payment_setup):
    data = payment_setup

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    rejected = reject_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=payment.id,
        recipient_id=data["alice_id"],
    )

    assert rejected.status == "rejected"
    assert rejected.confirmed_at is None

    db_session.expire_all()
    saved = db_session.get(Payment, payment.id)

    assert saved.status == "rejected"
    assert saved.confirmed_at is None


def test_sender_cannot_reject_payment(db_session, payment_setup):
    data = payment_setup

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # Bob reported the payment but cannot reject it.
    with pytest.raises(HTTPException) as exc:
        reject_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["bob_id"],
        )

    assert exc.value.status_code == 403
    assert payment.status == "pending"


def test_payment_cannot_be_rejected_twice(db_session, payment_setup):
    data = payment_setup

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    reject_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=payment.id,
        recipient_id=data["alice_id"],
    )

    with pytest.raises(HTTPException) as exc:
        reject_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["alice_id"],
        )

    assert exc.value.status_code == 409


def test_confirmed_payment_cannot_be_rejected(db_session, payment_setup):
    data = payment_setup

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # Alice confirms the payment.
    confirm_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=payment.id,
        recipient_id=data["alice_id"],
    )

    # Alice cannot reverse it through the reject endpoint.
    with pytest.raises(HTTPException) as exc:
        reject_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["alice_id"],
        )

    assert exc.value.status_code == 409



def test_payment_exceeding_outstanding_debt_is_rejected(
    db_session, payment_setup
):
    data = payment_setup

    # Bob owes Alice $50, but reports paying $60.
    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("60.00"),
        ),
    )

    # Alice must not be able to confirm the overpayment.
    with pytest.raises(HTTPException) as exc:
        confirm_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["alice_id"],
        )

    assert exc.value.status_code == 409

    db_session.refresh(payment)
    assert payment.status == "pending"


def test_payment_after_full_settlement_is_rejected(
    db_session, payment_setup
):
    data = payment_setup

    # Bob pays the entire $50 debt.
    first_payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("50.00"),
        ),
    )

    confirm_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=first_payment.id,
        recipient_id=data["alice_id"],
    )

    # Bob reports another $10 after settling his debt.
    second_payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("10.00"),
        ),
    )

    with pytest.raises(HTTPException) as exc:
        confirm_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=second_payment.id,
            recipient_id=data["alice_id"],
        )

    assert exc.value.status_code == 409

    db_session.refresh(second_payment)
    assert second_payment.status == "pending"



def test_create_payment_rolls_back_when_flush_fails(
    db_session, payment_setup, monkeypatch
):
    data = payment_setup

    payload = PaymentCreate(
        to_user_id=data["alice_id"],
        amount=Decimal("30.00"),
    )

    # Save the real flush and rollback methods.
    original_flush = db_session.flush
    original_rollback = db_session.rollback

    rollback_called = []

    # Simulate a PostgreSQL failure during INSERT.
    def failing_flush(*args, **kwargs):
        raise RuntimeError("Simulated database failure")

    # Record when rollback is called, then perform it.
    def tracking_rollback():
        rollback_called.append(True)
        original_rollback()

    # Temporarily replace the session methods.
    monkeypatch.setattr(db_session, "flush", failing_flush)
    monkeypatch.setattr(db_session, "rollback", tracking_rollback)

    # Payment creation must propagate the failure.
    with pytest.raises(RuntimeError, match="Simulated database failure"):
        create_payment(
            db=db_session,
            group_id=data["group_id"],
            sender_id=data["bob_id"],
            payload=payload,
        )

    # Verify the service explicitly rolled back.
    assert rollback_called == [True]

    # Restore the original flush method before querying.
    monkeypatch.setattr(db_session, "flush", original_flush)

    # Verify that no payment was saved.
    from sqlalchemy import select

    payments = db_session.scalars(
        select(Payment).where(
            Payment.group_id == data["group_id"]
        )
    ).all()

    assert payments == []


def test_outsider_cannot_confirm_payment(db_session, payment_setup):
    data = payment_setup

    # Bob reports a $30 payment to Alice.
    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # An outsider attempts to confirm Bob's payment.
    with pytest.raises(HTTPException) as exc:
        confirm_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["outsider_id"],
        )

    # Only Alice, the intended recipient, can confirm it.
    assert exc.value.status_code == 403

    # The unauthorized attempt must not change the payment.
    db_session.refresh(payment)
    assert payment.status == "pending"
    assert payment.confirmed_at is None



def test_unrelated_group_member_cannot_confirm_payment(
    db_session, payment_setup
):
    data = payment_setup

    # Add the existing third user to the group as Charlie.
    db_session.add(
        GroupMember(
            group_id=data["group_id"],
            user_id=data["outsider_id"],
            role="member",
        )
    )
    db_session.flush()

    # Bob reports paying Alice $30.
    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # Charlie is a group member but is not the recipient.
    with pytest.raises(HTTPException) as exc:
        confirm_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["outsider_id"],
        )

    assert exc.value.status_code == 403

    # Unauthorized confirmation must not change the payment.
    db_session.refresh(payment)
    assert payment.status == "pending"
    assert payment.confirmed_at is None



def test_unrelated_group_member_cannot_reject_payment(
    db_session, payment_setup
):
    data = payment_setup

    # Add the third user to the group.
    db_session.add(
        GroupMember(
            group_id=data["group_id"],
            user_id=data["outsider_id"],
            role="member",
        )
    )
    db_session.flush()

    # Bob reports paying Alice $30.
    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # Charlie attempts to reject Bob's payment.
    with pytest.raises(HTTPException) as exc:
        reject_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["outsider_id"],
        )

    # Only Alice can reject this payment.
    assert exc.value.status_code == 403

    # The payment must remain unchanged.
    db_session.refresh(payment)
    assert payment.status == "pending"
    assert payment.confirmed_at is None



def test_outsider_cannot_reject_payment(db_session, payment_setup):
    data = payment_setup

    # Bob reports a $30 payment to Alice.
    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    # An outsider attempts to reject Bob's payment.
    with pytest.raises(HTTPException) as exc:
        reject_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["outsider_id"],
        )

    # Only the intended recipient may reject.
    assert exc.value.status_code == 403

    # The unauthorized attempt must not modify the payment.
    db_session.refresh(payment)
    assert payment.status == "pending"
    assert payment.confirmed_at is None




def test_confirm_payment_does_not_refresh_after_commit(
    db_session, payment_setup, monkeypatch
):
    data = payment_setup

    # Bob reports paying Alice $30.
    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    original_commit = db_session.commit
    commit_completed = False

    def tracking_commit():
        nonlocal commit_completed
        original_commit()
        commit_completed = True

    original_refresh = db_session.refresh

    def guarded_refresh(*args, **kwargs):
        if commit_completed:
            raise RuntimeError("Refresh attempted after commit")
        return original_refresh(*args, **kwargs)

    # Detect a refresh after a successful commit.
    monkeypatch.setattr(db_session, "commit", tracking_commit)
    monkeypatch.setattr(db_session, "refresh", guarded_refresh)

    confirmed = confirm_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=payment.id,
        recipient_id=data["alice_id"],
    )

    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_at is not None


def test_reject_payment_does_not_refresh_after_commit(
    db_session, payment_setup, monkeypatch
):
    data = payment_setup

    payment = create_payment(
        db=db_session,
        group_id=data["group_id"],
        sender_id=data["bob_id"],
        payload=PaymentCreate(
            to_user_id=data["alice_id"],
            amount=Decimal("30.00"),
        ),
    )

    original_commit = db_session.commit
    commit_completed = False

    def tracking_commit():
        nonlocal commit_completed
        original_commit()
        commit_completed = True

    original_refresh = db_session.refresh

    def guarded_refresh(*args, **kwargs):
        if commit_completed:
            raise RuntimeError("Refresh attempted after commit")
        return original_refresh(*args, **kwargs)

    monkeypatch.setattr(db_session, "commit", tracking_commit)
    monkeypatch.setattr(db_session, "refresh", guarded_refresh)

    rejected = reject_payment(
        db=db_session,
        group_id=data["group_id"],
        payment_id=payment.id,
        recipient_id=data["alice_id"],
    )

    assert rejected.status == "rejected"
    assert rejected.confirmed_at is None


def test_reject_payment_rolls_back_on_conflict(db_session, payment_setup):
    data = payment_setup

    # Create a payment that has already been rejected.
    payment = Payment(
        group_id=data["group_id"],
        from_user_id=data["bob_id"],
        to_user_id=data["alice_id"],
        amount=Decimal("30.00"),
        status="rejected",
    )

    db_session.add(payment)
    db_session.commit()

    # Attempting to reject it again should fail.
    with pytest.raises(HTTPException) as exc:
        reject_payment(
            db=db_session,
            group_id=data["group_id"],
            payment_id=payment.id,
            recipient_id=data["alice_id"],
        )

    # Verify the expected API error.
    assert exc.value.status_code == 409

    # A failed operation should not leave an open transaction.
    assert not db_session.in_transaction()
