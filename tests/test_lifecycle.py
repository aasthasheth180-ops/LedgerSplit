from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from tests.test_payment_service import payment_setup

from app.models.group import Group
from app.models.expense import Expense

from app.schemas.expense import ExpenseCreate

from app.services.group_service import (
    create_group,
    get_user_groups,
    get_group_members,
)

from app.services.expense_service import (
    create_expense,
    get_group_expenses,
    get_expense_details,
)

from app.services.ledger_service import calculate_group_balances

from app.services.lifecycle_service import (
    delete_group,
    archive_group,
    void_expense,
)


def test_delete_empty_group(db_session, payment_setup):
    owner = payment_setup["alice_id"]

    group = create_group(
        db_session,
        "Empty group",
        owner,
    )

    gid = group.id

    delete_group(db_session, gid, owner)

    db_session.expire_all()

    assert db_session.get(Group, gid).deleted_at is not None

    assert gid not in [
        g.id for g in get_user_groups(db_session, owner)
    ]

    with pytest.raises(HTTPException) as exc:
        get_group_members(db_session, gid, owner)

    assert exc.value.status_code == 404

    # Repeated deletion must be safe.
    delete_group(db_session, gid, owner)


def test_non_owner_cannot_delete(db_session, payment_setup):
    d = payment_setup

    with pytest.raises(HTTPException) as exc:
        delete_group(
            db_session,
            d["group_id"],
            d["bob_id"],
        )

    assert exc.value.status_code == 403


def test_group_with_history_cannot_be_deleted(
    db_session, payment_setup
):
    d = payment_setup

    with pytest.raises(HTTPException) as exc:
        delete_group(
            db_session,
            d["group_id"],
            d["alice_id"],
        )

    assert exc.value.status_code == 409


def test_unsettled_group_cannot_be_archived(
    db_session, payment_setup
):
    d = payment_setup

    with pytest.raises(HTTPException) as exc:
        archive_group(
            db_session,
            d["group_id"],
            d["alice_id"],
        )

    assert exc.value.status_code == 409


def test_void_expense_recalculates_balances(
    db_session, payment_setup
):
    d = payment_setup
    gid = d["group_id"]
    owner = d["alice_id"]

    expense = db_session.scalar(
        select(Expense).where(
            Expense.group_id == gid
        )
    )

    eid = expense.id

    before = calculate_group_balances(db_session, gid)

    assert before[owner] == Decimal("50.00")

    void_expense(db_session, gid, eid, owner)

    db_session.expire_all()

    assert db_session.get(Expense, eid).voided_at is not None

    after = calculate_group_balances(db_session, gid)

    assert all(amount == 0 for amount in after.values())

    assert get_group_expenses(
        db_session, gid, owner
    ) == []

    with pytest.raises(HTTPException) as exc:
        get_expense_details(
            db_session, gid, eid, owner
        )

    assert exc.value.status_code == 404

    # Repeated deletion must not change balances again.
    void_expense(db_session, gid, eid, owner)

    assert calculate_group_balances(
        db_session, gid
    ) == after


def test_non_payer_cannot_void_expense(
    db_session, payment_setup
):
    d = payment_setup

    expense = db_session.scalar(
        select(Expense).where(
            Expense.group_id == d["group_id"]
        )
    )

    with pytest.raises(HTTPException) as exc:
        void_expense(
            db_session,
            d["group_id"],
            expense.id,
            d["bob_id"],
        )

    assert exc.value.status_code == 403


def test_archived_group_is_read_only(
    db_session, payment_setup
):
    owner = payment_setup["alice_id"]

    group = create_group(
        db_session,
        "Archive test",
        owner,
    )

    gid = group.id

    archived = archive_group(
        db_session, gid, owner
    )

    assert archived.archived_at is not None

    # Archived history remains accessible.
    assert gid in [
        g.id for g in get_user_groups(db_session, owner)
    ]

    assert get_group_members(
        db_session, gid, owner
    )

    assert get_group_expenses(
        db_session, gid, owner
    ) == []

    payload = ExpenseCreate(
        description="Blocked expense",
        amount=Decimal("10.00"),
        splits=[
            {
                "user_id": owner,
                "amount_owed": Decimal("10.00"),
            }
        ],
    )

    with pytest.raises(HTTPException) as exc:
        create_expense(
            db_session,
            gid,
            owner,
            payload,
        )

    assert exc.value.status_code == 409