from decimal import Decimal
import pytest
from fastapi import HTTPException
from tests.test_payment_service import payment_setup
from tests.test_payment_requests import request
from app.models.group import Group
from app.schemas.expense import ExpenseCreate
from app.schemas.payment import PaymentCreate
from app.services.expense_service import create_expense
from app.services.payment_service import create_payment

@pytest.mark.parametrize("kind",["expense_total","expense_split","payment","payment_key","request"])
def test_jpy_rejects_fraction(db_session,payment_setup,kind):
    db,d=db_session,payment_setup
    db.get(Group,d["group_id"]).currency="JPY"
    db.commit()
    with pytest.raises(HTTPException) as e:
        if kind.startswith("expense"):
            amount="10.50" if kind=="expense_total" else "10.00"
            create_expense(db,d["group_id"],d["alice_id"],ExpenseCreate(description="JPY",amount=Decimal(amount),splits=[{"user_id":d["alice_id"],"amount_owed":"5.50"},{"user_id":d["bob_id"],"amount_owed":"5.00" if kind=="expense_total" else "4.50"}]))
        elif kind.startswith("payment"):
            create_payment(db,d["group_id"],d["bob_id"],PaymentCreate(to_user_id=d["alice_id"],amount=Decimal("1.50")),"jpy" if kind=="payment_key" else None)
        else:
            request(db,d,"1.50")
    assert e.value.status_code==422


def test_jpy_accepts_whole_request(db_session,payment_setup):
    db,d=db_session,payment_setup
    db.get(Group,d["group_id"]).currency="JPY"
    db.commit()
    assert request(db,d,"10.00").amount==Decimal("10.00")
