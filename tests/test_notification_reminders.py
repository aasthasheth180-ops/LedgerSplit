from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from tests.test_payment_service import payment_setup
from app.models.notification import Notification
from app.models.user import User
from app.schemas.payment import PaymentCreate
from app.schemas.payment_request import PaymentRequestCreate
from app.services.payment_request_service import create_payment_request
from app.services.payment_service import create_payment, confirm_payment, reject_payment
from app.services.notification_service import generate_reminders

@pytest.fixture
def scenario(db_session, payment_setup):
    d = payment_setup
    r = create_payment_request(db_session, d["group_id"], d["alice_id"], PaymentRequestCreate(debtor_id=d["bob_id"], amount=Decimal("50.00")))
    return db_session, d, r

def count(db, prefix, ident, user):
    return len(db.scalars(select(Notification).where(Notification.event_key.like(f"{prefix}:{ident}:%"), Notification.user_id == user)).all())

def report(db, d):
    return create_payment(db, d["group_id"], d["bob_id"], PaymentCreate(to_user_id=d["alice_id"], amount=Decimal("50.00")))

def test_request_before_48_hours(scenario):
    db,d,r = scenario
    generate_reminders(db, r.created_at + timedelta(hours=47))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 0

def test_request_at_48_hours(scenario):
    db,d,r = scenario
    generate_reminders(db, r.created_at + timedelta(hours=48))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 1

def test_no_duplicate(scenario):
    db,d,r = scenario
    now = r.created_at + timedelta(hours=48)
    generate_reminders(db, now)
    generate_reminders(db, now + timedelta(minutes=1))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 1

def test_repeat_after_48_hours(scenario):
    db,d,r = scenario
    now = r.created_at + timedelta(hours=48)
    generate_reminders(db, now)
    generate_reminders(db, now + timedelta(hours=47))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 1
    generate_reminders(db, now + timedelta(hours=48))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 2

def test_reported_payment_shifts_reminders(scenario):
    db,d,r = scenario
    p = report(db,d)
    generate_reminders(db, max(p.created_at,r.created_at) + timedelta(hours=48))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 0
    assert count(db,"confirmation-reminder",p.id,d["alice_id"]) == 1

def test_confirmed_payment_stops_reminders(scenario):
    db,d,r = scenario
    p = report(db,d)
    now = max(p.created_at,r.created_at) + timedelta(hours=48)
    generate_reminders(db, now)
    confirm_payment(db,d["group_id"],p.id,d["alice_id"])
    generate_reminders(db, now + timedelta(hours=48))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 0
    assert count(db,"confirmation-reminder",p.id,d["alice_id"]) == 1

def test_rejected_payment_resumes_request(scenario):
    db,d,r = scenario
    p = report(db,d)
    reject_payment(db,d["group_id"],p.id,d["alice_id"])
    generate_reminders(db, max(p.created_at,r.created_at) + timedelta(hours=48))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 1
    assert count(db,"confirmation-reminder",p.id,d["alice_id"]) == 0

def test_disabled_reminders(scenario):
    db,d,r = scenario
    db.get(User,d["bob_id"]).reminders_enabled = False
    db.flush()
    generate_reminders(db, r.created_at + timedelta(hours=48))
    assert count(db,"request-reminder",r.id,d["bob_id"]) == 0
