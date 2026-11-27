from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import select, delete, text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from tests.conftest import test_engine
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.payment_request import PaymentRequest
from app.schemas.payment_request import PaymentRequestCreate
from app.services.payment_request_service import create_payment_request
from app.services.group_service import create_group


def test_concurrent_request_creation():
    assert test_engine.url.database=="ledgersplit_test_db"
    ids=[]
    gid=None
    try:
        with Session(test_engine) as db:
            users=[User(full_name="Race User",email=f"{uuid4().hex}@example.com",hashed_password="test_hash") for _ in range(2)]
            db.add_all(users); db.flush()
            ids=[u.id for u in users]
            g=Group(name="Request race",created_by=ids[0]); db.add(g); db.flush(); gid=g.id
            db.add_all([GroupMember(group_id=gid,user_id=uid,role=role) for uid,role in zip(ids,["owner","member"])])
            e=Expense(group_id=gid,paid_by=ids[0],description="Race",amount=Decimal("50.00")); db.add(e); db.flush()
            db.add(ExpenseSplit(expense_id=e.id,user_id=ids[1],amount_owed=Decimal("50.00")))
            db.commit()
        barrier=Barrier(2)
        def worker(key):
            with Session(test_engine) as db:
                db.execute(text("SET LOCAL lock_timeout = '10s'"))
                barrier.wait(timeout=10)
                try:
                    r=create_payment_request(db,gid,ids[0],PaymentRequestCreate(debtor_id=ids[1],amount=Decimal("30.00")),key)
                    return (201,r.id)
                except HTTPException as e:
                    return (e.status_code,None)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(worker,["race-a","race-b"]))
        assert sorted(x[0] for x in results)==[201,409]
        with Session(test_engine) as db:
            assert len(db.scalars(select(PaymentRequest).where(PaymentRequest.group_id==gid)).all())==1
    finally:
        with Session(test_engine) as db:
            if gid is not None:
                db.execute(delete(PaymentRequest).where(PaymentRequest.group_id==gid))
                db.execute(delete(ExpenseSplit).where(ExpenseSplit.expense_id.in_(select(Expense.id).where(Expense.group_id==gid))))
                db.execute(delete(Expense).where(Expense.group_id==gid))
                db.execute(delete(GroupMember).where(GroupMember.group_id==gid))
                db.execute(delete(Group).where(Group.id==gid))
            if ids: db.execute(delete(User).where(User.id.in_(ids)))
            db.commit()
