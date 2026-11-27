from decimal import Decimal
import pytest
from fastapi import HTTPException
from tests.test_payment_service import payment_setup
from tests.test_payment_requests import request
from app.models.payment_request import PaymentRequest
from app.schemas.payment import PaymentCreate
from app.services.payment_service import create_payment, confirm_payment, reject_payment
from app.services.ledger_service import calculate_group_balances


def report(db,d,amount):
    return create_payment(db,d["group_id"],d["bob_id"],PaymentCreate(to_user_id=d["alice_id"],amount=Decimal(amount)))


def test_partial_full_and_retry(db_session,payment_setup):
    db,d=db_session,payment_setup
    rid=request(db,d).id
    p=report(db,d,"10.00")
    assert db.get(PaymentRequest,rid).fulfilled_amount == 0
    confirm_payment(db,d["group_id"],p.id,d["alice_id"])
    db.expire_all()
    assert db.get(PaymentRequest,rid).fulfilled_amount == Decimal("10.00")
    assert db.get(PaymentRequest,rid).status == "pending"
    try:
        confirm_payment(db,d["group_id"],p.id,d["alice_id"])
    except HTTPException as e:
        assert e.status_code == 409
    db.expire_all()
    assert db.get(PaymentRequest,rid).fulfilled_amount == Decimal("10.00")
    p=report(db,d,"25.00")
    confirm_payment(db,d["group_id"],p.id,d["alice_id"])
    db.expire_all()
    r=db.get(PaymentRequest,rid)
    assert r.fulfilled_amount == Decimal("30.00") and r.status == "fulfilled" and r.resolved_at is not None
    balances=calculate_group_balances(db,d["group_id"])
    assert balances[d["alice_id"]] == Decimal("15.00")
    assert sum(balances.values()) == 0


def test_rejection_does_not_fulfill(db_session,payment_setup):
    db,d=db_session,payment_setup
    rid=request(db,d).id
    p=report(db,d,"10.00")
    reject_payment(db,d["group_id"],p.id,d["alice_id"])
    db.expire_all()
    assert db.get(PaymentRequest,rid).fulfilled_amount == 0


def test_reconciliation_failure_rolls_back(db_session,payment_setup,monkeypatch):
    from app.models.payment import Payment
    import app.services.payment_service as service
    db,d=db_session,payment_setup
    rid=request(db,d).id
    pid=report(db,d,"10.00").id
    original=service.reconcile_payment_request
    def fail(**kwargs):
        original(**kwargs)
        raise RuntimeError("injected failure")
    monkeypatch.setattr(service,"reconcile_payment_request",fail)
    with pytest.raises(RuntimeError,match="injected failure"):
        confirm_payment(db,d["group_id"],pid,d["alice_id"])
    db.expire_all()
    assert db.get(Payment,pid).status == "pending"
    assert db.get(PaymentRequest,rid).fulfilled_amount == 0
