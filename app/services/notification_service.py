from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.payment_request import PaymentRequest
from app.models.group import Group
from app.models.user import User
from app.services.ledger_service import calculate_group_balances

def notify(db, user_id, key, message, created_at=None):
    values = dict(user_id=user_id, event_key=key, message=message)
    if created_at is not None:
        values["created_at"] = created_at
    db.execute(insert(Notification).values(**values).on_conflict_do_nothing(index_elements=[Notification.event_key]))

def generate_reminders(db, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)
    groups = db.scalars(select(Group.id).where(Group.id.in_(select(Payment.group_id).where(Payment.status == "pending").union(select(PaymentRequest.group_id).where(PaymentRequest.status == "pending")))).order_by(Group.id)).all()
    for group_id in groups:
        db.scalar(select(Group).where(Group.id == group_id).with_for_update())
        pending = db.scalars(select(Payment).where(Payment.group_id == group_id, Payment.status == "pending")).all()
        def remind(user_id, key, message, created):
            user = db.get(User, user_id)
            if not user or not user.is_active or not user.reminders_enabled or created > cutoff:
                return
            latest = db.scalar(select(Notification.created_at).where(Notification.event_key.like(key + ":%")).order_by(Notification.created_at.desc()).limit(1))
            if latest is None or latest <= cutoff:
                bucket = int((now-created).total_seconds() // 172800)
                notify(db, user_id, f"{key}:{bucket}", message, created_at=now)
        for p in pending:
            remind(p.to_user_id, f"confirmation-reminder:{p.id}", f"Payment #{p.id} is awaiting your confirmation.", p.created_at)
        balances = calculate_group_balances(db, group_id)
        for r in db.scalars(select(PaymentRequest).where(PaymentRequest.group_id == group_id, PaymentRequest.status == "pending")).all():
            outstanding = min(r.amount-r.fulfilled_amount, balances.get(r.requester_id, 0), -balances.get(r.debtor_id, 0))
            reported = sum(p.amount for p in pending if p.from_user_id == r.debtor_id and p.to_user_id == r.requester_id)
            if outstanding > reported:
                remind(r.debtor_id, f"request-reminder:{r.id}", f"Payment request #{r.id} remains outstanding.", r.created_at)
        db.commit()
