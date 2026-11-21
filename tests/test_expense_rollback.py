from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.services.expense_service import create_expense
from app.schemas.expense import ExpenseCreate


def test_expense_creation_rolls_back_when_split_flush_fails(
    client, db_session, monkeypatch
):
    # Arrange: create a user and a group through the API.
    email = f"rollback_{uuid4().hex}@example.com"
    password = "TestPassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Rollback Tester",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    group_response = client.post(
        "/groups",
        json={"name": "Rollback Test Group"},
        headers=headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # One participant is sufficient to test transaction rollback.
    payload = ExpenseCreate(
        description="Rollback Test Expense",
        amount=Decimal("100.00"),
        splits=[
            {
                "user_id": user_id,
                "amount_owed": Decimal("100.00"),
            }
        ],
    )

    original_flush = db_session.flush
    flush_count = 0

    def failing_flush(*args, **kwargs):
        nonlocal flush_count
        flush_count += 1

        if flush_count == 2:
            raise RuntimeError("Simulated database failure")

        return original_flush(*args, **kwargs)

    # Replace flush only for this test.
    monkeypatch.setattr(db_session, "flush", failing_flush)

    # Act: the second flush should raise an exception.
    with pytest.raises(RuntimeError, match="Simulated database failure"):
        create_expense(
            db=db_session,
            group_id=group_id,
            payer_id=user_id,
            payload=payload,
        )

    # Verify that both intended flush operations were reached.
    assert flush_count == 2

    # Verify that the failed transaction left no expense or splits.
    saved_expenses = db_session.scalars(
        select(Expense).where(
            Expense.group_id == group_id,
            Expense.description == "Rollback Test Expense",
        )
    ).all()

    assert saved_expenses == []

    saved_splits = db_session.scalars(
        select(ExpenseSplit).join(Expense).where(
            Expense.group_id == group_id,
            Expense.description == "Rollback Test Expense",
        )
    ).all()

    assert saved_splits == []