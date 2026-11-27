from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException
from tests.test_payment_service import payment_setup
from app.schemas.payment_request import PaymentRequestCreate
from app.services.payment_request_service import create_payment_request, list_payment_requests, cancel_payment_request
from app.services.group_service import remove_group_member
from app.models.payment_request import PaymentRequest


def request(db, d, amount="30.00", key=None, **kwargs):
    return create_payment_request(db, d["group_id"], d["alice_id"], PaymentRequestCreate(debtor_id=d["bob_id"], amount=Decimal(amount), **kwargs), key)


def test_create_list_retry_cancel(db_session, payment_setup):
    d = payment_setup
    r = request(db_session, d, key="request-1", description="Dinner", due_date=date(2030, 1, 1))
    rid = r.id
    assert r.status == "pending" and r.fulfilled_amount == 0
    assert request(db_session, d, key="request-1", description="Dinner", due_date=date(2030, 1, 1)).id == rid
    db_session.expire_all()
    saved = list_payment_requests(db_session, d["group_id"], d["bob_id"])
    assert len(saved) == 1 and saved[0].id == rid
    assert saved[0].description == "Dinner" and saved[0].due_date == date(2030, 1, 1)
    with pytest.raises(HTTPException) as e:
        cancel_payment_request(db_session, d["group_id"], rid, d["bob_id"])
    assert e.value.status_code == 403
    cancelled = cancel_payment_request(db_session, d["group_id"], rid, d["alice_id"])
    assert cancelled.status == "cancelled" and cancelled.resolved_at is not None
    db_session.expire_all()
    assert db_session.get(PaymentRequest, rid).status == "cancelled"


@pytest.mark.parametrize("case,code", [("over",409),("self",400),("outsider",400),("unauthorized",403),("reverse",409)])
def test_invalid_request(db_session, payment_setup, case, code):
    d = payment_setup
    requester, debtor, amount = d["alice_id"], d["bob_id"], "30.00"
    if case == "over": amount = "50.01"
    if case == "self": debtor = requester
    if case == "outsider": debtor = d["outsider_id"]
    if case == "unauthorized": requester = d["outsider_id"]
    if case == "reverse": requester, debtor = debtor, requester
    with pytest.raises(HTTPException) as e:
        create_payment_request(db_session, d["group_id"], requester, PaymentRequestCreate(debtor_id=debtor, amount=Decimal(amount)))
    assert e.value.status_code == code


def test_duplicate_and_conflicting_key(db_session, payment_setup):
    d = payment_setup
    request(db_session, d, key="same")
    for key in ("same", "different", None):
        with pytest.raises(HTTPException) as e:
            request(db_session, d, amount="20.00", key=key)
        assert e.value.status_code == 409


def test_list_outsider(db_session, payment_setup):
    with pytest.raises(HTTPException) as e:
        list_payment_requests(db_session, payment_setup["group_id"], payment_setup["outsider_id"])
    assert e.value.status_code == 403


def test_request_routes_require_auth(client):
    for method, path in [("GET", "/groups/1/payment-requests"), ("POST", "/groups/1/payment-requests"), ("POST", "/groups/1/payment-requests/1/cancel")]:
        assert client.request(method, path, json={"debtor_id":2,"amount":"1.00"} if method == "POST" else None).status_code == 401
