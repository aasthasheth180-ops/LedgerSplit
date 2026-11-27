from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException
from tests.test_payment_service import payment_setup
from app.schemas.expense import ExpenseCreate
from app.models.expense import Expense
from app.services.expense_service import create_expense


def test_metadata_persistence_and_retry(db_session,payment_setup):
    db,d=db_session,payment_setup
    payload=ExpenseCreate(description="Train",amount=Decimal("12.00"),category="Travel",expense_date=date(2026,11,26),reference="ticket-1",split_method="Equal",splits=[{"user_id":d["alice_id"],"amount_owed":"6.00"},{"user_id":d["bob_id"],"amount_owed":"6.00"}])
    expense,_=create_expense(db,d["group_id"],d["alice_id"],payload,"metadata-1")
    eid=expense.id
    db.expire_all()
    saved=db.get(Expense,eid)
    assert (saved.category,saved.expense_date,saved.reference,saved.split_method)==("Travel",date(2026,11,26),"ticket-1","Equal")
    retry,_=create_expense(db,d["group_id"],d["alice_id"],payload,"metadata-1")
    assert retry.id==eid
    for field,value in [("category","Other"),("reference","ticket-2"),("split_method","Exact"),("expense_date",date(2026,11,25))]:
        with pytest.raises(HTTPException) as e:
            create_expense(db,d["group_id"],d["alice_id"],payload.model_copy(update={field:value}),"metadata-1")
        assert e.value.status_code==409
