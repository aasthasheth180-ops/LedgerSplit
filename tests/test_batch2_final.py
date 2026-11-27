from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.payment import Payment
from app.models.payment_request import PaymentRequest
from app.schemas.expense import ExpenseCreate
from app.schemas.payment import PaymentCreate
from app.schemas.payment_request import PaymentRequestCreate
from app.services.group_service import create_group, remove_group_member
from app.services.expense_service import create_expense
from app.services.payment_service import create_payment, confirm_payment
from app.services.payment_request_service import create_payment_request
from tests.conftest import test_engine
from tests.test_payment_service import payment_setup


def test_authenticated_request_journey(client):
    users, headers = {}, {}
    for name in ('alice', 'bob', 'outsider'):
        email = f'{uuid4().hex}@example.com'
        credentials = {'email': email, 'password': 'TestPassword123!'}
        r = client.post('/auth/register', json={**credentials, 'full_name': name.title()})
        assert r.status_code == 201, r.text
        users[name] = r.json()['id']
        r = client.post('/auth/login', json=credentials)
        assert r.status_code == 200, r.text
        headers[name] = {'Authorization': f"Bearer {r.json()['access_token']}"}
    a, b = users['alice'], users['bob']
    ah, bh, oh = (headers[k] for k in ('alice', 'bob', 'outsider'))
    r = client.post('/groups', json={'name': 'Request journey'}, headers=ah)
    assert r.status_code == 201, r.text
    base = f"/groups/{r.json()['id']}"
    assert client.post(base+'/members', json={'user_id': b}, headers=ah).status_code == 201
    r = client.post(base+'/expenses', headers=ah, json={'description':'Dinner','amount':'100.00','splits':[{'user_id':a,'amount_owed':'50.00'},{'user_id':b,'amount_owed':'50.00'}]})
    assert r.status_code == 201, r.text
    path = base+'/payment-requests'
    payload = {'debtor_id':b,'amount':'40.00','description':'Dinner','due_date':'2030-01-01'}
    keyed = {**ah,'Idempotency-Key':uuid4().hex}
    r = client.post(path, json=payload, headers=keyed)
    assert r.status_code == 201, r.text
    rid = r.json()['id']
    assert r.json()['status'] == 'pending'
    retry = client.post(path, json=payload, headers=keyed)
    assert retry.status_code == 201 and retry.json()['id'] == rid
    assert client.get(path, headers=oh).status_code == 403
    assert client.post(path, json=payload, headers=oh).status_code == 403
    assert client.post(f'{path}/{rid}/cancel', headers=bh).status_code == 403
    for amount, expected, status in [('15.00','15.00','pending'),('25.00','40.00','fulfilled')]:
        r = client.post(base+'/payments', headers=bh, json={'to_user_id':a,'amount':amount})
        assert r.status_code == 201, r.text
        confirm = f"{base}/payments/{r.json()['id']}/confirm"
        assert client.post(confirm, headers=ah).status_code == 200
        assert client.post(confirm, headers=ah).status_code == 409
        r = client.get(path, headers=bh)
        assert r.status_code == 200, r.text
        assert len(r.json()) == 1
        assert Decimal(r.json()[0]['fulfilled_amount']) == Decimal(expected)
        assert r.json()[0]['status'] == status
    assert client.post(f'{path}/{rid}/cancel', headers=ah).status_code == 409
    r = client.post(path, headers=ah, json={'debtor_id':b,'amount':'10.00'})
    assert r.status_code == 201, r.text
    r = client.post(f"{path}/{r.json()['id']}/cancel", headers=ah)
    assert r.status_code == 200 and r.json()['status'] == 'cancelled'


@pytest.mark.parametrize('status', ['pending', 'cancelled', 'fulfilled'])
def test_request_history_alone_blocks_member_removal(db_session, payment_setup, status):
    # Isolate the request-history guard from expense/payment history guards.
    d = payment_setup
    gid, a, b = d['group_id'], d['alice_id'], d['bob_id']
    db_session.execute(delete(ExpenseSplit).where(ExpenseSplit.expense_id.in_(select(Expense.id).where(Expense.group_id == gid))))
    db_session.execute(delete(Expense).where(Expense.group_id == gid))
    from datetime import datetime, timezone
    db_session.add(PaymentRequest(group_id=gid, requester_id=a, debtor_id=b, amount=Decimal('30'), fulfilled_amount=Decimal('30' if status == 'fulfilled' else '0'), status=status, resolved_at=None if status == 'pending' else datetime.now(timezone.utc)))
    db_session.commit()
    with pytest.raises(HTTPException) as exc:
        remove_group_member(db_session, gid, b, a)
    assert exc.value.status_code == 409
    assert db_session.scalar(select(GroupMember.id).where(GroupMember.group_id == gid, GroupMember.user_id == b)) is not None


def run_blocked(lock, operation):
    ready = Event()
    worker_pid = []
    def worker():
        with Session(test_engine, expire_on_commit=False) as db:
            db.execute(text("SET LOCAL lock_timeout = '10s'"))
            worker_pid.append(db.scalar(text('SELECT pg_backend_pid()')))
            ready.set()
            try:
                return operation(db)
            except HTTPException as exc:
                db.rollback()
                return ('error', exc.status_code)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with Session(test_engine, expire_on_commit=False) as db:
            pid = db.scalar(text('SELECT pg_backend_pid()'))
            db.scalar(lock.with_for_update())
            future = pool.submit(worker)
            assert ready.wait(5)
            deadline = monotonic()+5
            while monotonic() < deadline:
                if pid in db.scalar(text('SELECT pg_blocking_pids(:pid)'), {'pid':worker_pid[0]}):
                    break
                sleep(.05)
            else:
                pytest.fail('Competing operation did not wait for row lock')
            first = operation(db)
        return first, future.result(timeout=15)


@pytest.fixture
def committed_users():
    assert test_engine.url.database == 'ledgersplit_test_db'
    ids = []
    try:
        with Session(test_engine) as db:
            users = [User(full_name=n,email=f'{uuid4().hex}@example.com',hashed_password='test_hash') for n in ('Alice','Bob')]
            db.add_all(users)
            db.flush()
            ids = [u.id for u in users]
            db.commit()
        yield ids
    finally:
        if ids:
            with Session(test_engine) as db:
                groups = select(Group.id).where(Group.created_by.in_(ids))
                db.execute(delete(PaymentRequest).where(PaymentRequest.group_id.in_(groups)))
                db.execute(delete(Payment).where(Payment.group_id.in_(groups)))
                db.execute(delete(ExpenseSplit).where(ExpenseSplit.expense_id.in_(select(Expense.id).where(Expense.group_id.in_(groups)))))
                db.execute(delete(Expense).where(Expense.group_id.in_(groups)))
                db.execute(delete(GroupMember).where(GroupMember.group_id.in_(groups)))
                db.execute(delete(Group).where(Group.created_by.in_(ids)))
                db.execute(delete(User).where(User.id.in_(ids)))
                db.commit()


def test_concurrent_group_idempotency(committed_users):
    a, _ = committed_users
    key = uuid4().hex
    def operation(db):
        return create_group(db, 'Concurrent group', a, idempotency_key=key).id
    first, second = run_blocked(select(User).where(User.id == a), operation)
    assert first == second
    with Session(test_engine) as db:
        assert list(db.scalars(select(Group.id).where(Group.created_by == a))) == [first]
        assert list(db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == first))) == [a]


def test_concurrent_confirmation_applies_request_once(committed_users):
    a, b = committed_users
    with Session(test_engine, expire_on_commit=False) as db:
        gid = create_group(db, 'Concurrent confirmation', a).id
        db.add(GroupMember(group_id=gid,user_id=b,role='member'))
        db.commit()
        create_expense(db,gid,a,ExpenseCreate(description='Dinner',amount=Decimal('50'),splits=[{'user_id':b,'amount_owed':Decimal('50')}]))
        rid = create_payment_request(db,gid,a,PaymentRequestCreate(debtor_id=b,amount=Decimal('40'))).id
        pid = create_payment(db,gid,b,PaymentCreate(to_user_id=a,amount=Decimal('15'))).id
    def operation(db):
        return confirm_payment(db,gid,pid,a).status
    first, second = run_blocked(select(Group).where(Group.id == gid), operation)
    assert first == 'confirmed'
    assert second == ('error',409)
    with Session(test_engine) as db:
        r = db.get(PaymentRequest,rid)
        assert r.fulfilled_amount == Decimal('15')
        assert r.status == 'pending'
        assert db.get(Payment,pid).status == 'confirmed'
