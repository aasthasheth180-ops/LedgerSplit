from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.schemas.expense import ExpenseCreate
from app.services.expense_service import create_expense
from app.services.group_service import create_group, remove_group_member
from tests.conftest import test_engine


def new_user(db):
    user = User(full_name="Atomicity Test", email=f"{uuid4().hex}@example.com", hashed_password=hash_password("TestPassword123!"))
    db.add(user)
    db.flush()
    return user


def test_group_creation_rolls_back_after_flush(db_session, monkeypatch):
    user = new_user(db_session)
    db_session.commit()
    uid = user.id
    name = f"rollback-{uuid4().hex}"
    def fail_commit():
        db_session.flush()
        raise RuntimeError("Injected failure before commit")
    with monkeypatch.context() as patch:
        patch.setattr(db_session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="Injected failure"):
            create_group(db_session, name, uid)
    assert db_session.scalar(select(Group.id).where(Group.name == name)) is None
    assert db_session.scalar(select(GroupMember.id).where(GroupMember.user_id == uid)) is None


@pytest.mark.parametrize("expense_first", [True, False])
def test_expense_and_removal_serialize(expense_first):
    # Independent committed sessions are required to exercise real PostgreSQL locks.
    assert test_engine.url.database == "ledgersplit_test_db"
    ids = []
    gid = None
    try:
        with Session(test_engine) as db:
            owner, member = new_user(db), new_user(db)
            ids = [owner.id, member.id]
            db.commit()
            group = create_group(db, f"race-{uuid4().hex}", ids[0])
            gid = group.id
            db.add(GroupMember(group_id=gid, user_id=ids[1], role="member"))
            db.commit()
        payload = ExpenseCreate(description="Race expense", amount=Decimal("10.00"), splits=[{"user_id": ids[1], "amount_owed": Decimal("10.00")}])
        def expense(db):
            return create_expense(db, gid, ids[0], payload)
        def remove(db):
            return remove_group_member(db, gid, ids[1], ids[0])
        first, second = (expense, remove) if expense_first else (remove, expense)
        ready = Event()
        worker_pid = []
        def competing():
            with Session(test_engine) as db:
                db.execute(text("SET LOCAL lock_timeout = '10s'"))
                worker_pid.append(db.scalar(text("SELECT pg_backend_pid()")))
                ready.set()
                try:
                    second(db)
                    return 200
                except HTTPException as exc:
                    db.rollback()
                    return exc.status_code
        with ThreadPoolExecutor(max_workers=1) as pool:
            with Session(test_engine) as db:
                pid = db.scalar(text("SELECT pg_backend_pid()"))
                db.scalar(select(Group).where(Group.id == gid).with_for_update())
                future = pool.submit(competing)
                assert ready.wait(5)
                deadline = monotonic() + 5
                blocked = False
                while monotonic() < deadline:
                    if pid in db.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": worker_pid[0]}):
                        blocked = True
                        break
                    sleep(0.05)
                assert blocked, "Competing operation did not wait for group lock"
                first(db)
            assert future.result(timeout=15) == (409 if expense_first else 400)
        with Session(test_engine) as db:
            membership = db.scalar(select(GroupMember.id).where(GroupMember.group_id == gid, GroupMember.user_id == ids[1]))
            expense_id = db.scalar(select(Expense.id).where(Expense.group_id == gid))
            assert (membership is not None) == expense_first
            assert (expense_id is not None) == expense_first
    finally:
        with Session(test_engine) as db:
            if gid is not None:
                db.execute(delete(ExpenseSplit).where(ExpenseSplit.expense_id.in_(select(Expense.id).where(Expense.group_id == gid))))
                db.execute(delete(Expense).where(Expense.group_id == gid))
                db.execute(delete(GroupMember).where(GroupMember.group_id == gid))
                db.execute(delete(Group).where(Group.id == gid))
            if ids:
                db.execute(delete(User).where(User.id.in_(ids)))
            db.commit()
