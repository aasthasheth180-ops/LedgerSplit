import hashlib
import json

from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.schemas.group import GroupUpdate
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.payment import Payment
from app.models.payment_request import PaymentRequest


def get_active_user_by_email(
    db: Session,
    email: str,
) -> User:
    user = db.scalar(
        select(User).where(
            User.email == email.strip().lower(),
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Active user not found",
        )

    return user


def lock_group(
    db: Session,
    group_id: int,
) -> Group:
    group = db.scalar(
        select(Group)
        .where(Group.id == group_id)
        .with_for_update()
    )

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Group not found",
        )

    return group


def get_membership(
    db: Session,
    group_id: int,
    user_id: int,
) -> GroupMember | None:
    return db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )


def create_group(
    db: Session,
    name: str,
    creator_id: int,
    *,
    description: str | None = None,
    category: str = "Home",
    custom_category: str | None = None,
    currency: str = "USD",
    default_split: str = "Equal",
    color: str = "#4a7856",
    member_emails: list[str] | None = None,
    idempotency_key: str | None = None,
) -> Group:
    try:
        name = name.strip()

        if not name:
            raise HTTPException(
                status_code=422,
                detail="Group name cannot be blank",
            )

        normalized_emails = sorted(
            email.strip().lower() for email in (member_emails or [])
        )
        request_data = {
            "name": name,
            "description": description,
            "category": category,
            "custom_category": custom_category,
            "currency": currency,
            "default_split": default_split,
            "color": color,
            "member_emails": normalized_emails,
        }
        fingerprint = hashlib.sha256(
            json.dumps(request_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        if idempotency_key is not None:
            db.scalar(select(User).where(User.id == creator_id).with_for_update())
            existing_group = db.scalar(
                select(Group).where(
                    Group.created_by == creator_id,
                    Group.idempotency_key == idempotency_key,
                )
            )
            if existing_group is not None:
                if existing_group.request_fingerprint != fingerprint:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency key already used for a different group",
                    )
                db.commit()
                return existing_group

        initial_member_ids = set()

        for email in normalized_emails:
            user = get_active_user_by_email(db, email)

            if user.id == creator_id:
                raise HTTPException(
                    status_code=400,
                    detail="The creator is already a group member",
                )

            if user.id in initial_member_ids:
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate initial group member",
                )

            initial_member_ids.add(user.id)

        group = Group(
            name=name,
            description=description,
            category=category,
            custom_category=custom_category,
            currency=currency,
            default_split=default_split,
            color=color,
            created_by=creator_id,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint if idempotency_key is not None else None,
        )

        db.add(group)
        db.flush()

        memberships = [
            GroupMember(
                group_id=group.id,
                user_id=creator_id,
                role="owner",
            )
        ]

        memberships.extend(
            GroupMember(
                group_id=group.id,
                user_id=user_id,
                role="member",
            )
            for user_id in sorted(initial_member_ids)
        )

        db.add_all(memberships)
        db.commit()
        db.refresh(group)

        return group

    except Exception:
        db.rollback()
        raise


def get_user_groups(
    db: Session,
    user_id: int,
) -> list[Group]:
    statement = (
        select(Group)
        .join(
            GroupMember,
            Group.id == GroupMember.group_id,
        )
        .where(GroupMember.user_id == user_id)
        .order_by(
            Group.created_at.desc(),
            Group.id.desc(),
        )
    )

    return list(db.scalars(statement).all())


def add_group_member(
    db: Session,
    group_id: int,
    user_id: int | None,
    requester_id: int,
    *,
    email: str | None = None,
) -> GroupMember:
    try:
        lock_group(db, group_id)

        requester = get_membership(
            db,
            group_id,
            requester_id,
        )

        if requester is None or requester.role != "owner":
            raise HTTPException(
                status_code=403,
                detail="Only group owners can add members",
            )

        if email is not None:
            user = get_active_user_by_email(db, email)
        else:
            user = db.get(User, user_id) if user_id else None

            if user is None:
                raise HTTPException(
                    status_code=404,
                    detail="User not found",
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=400,
                    detail="User account is inactive",
                )

        existing_member = get_membership(
            db,
            group_id,
            user.id,
        )

        if existing_member is not None:
            raise HTTPException(
                status_code=409,
                detail="User is already a group member",
            )

        member = GroupMember(
            group_id=group_id,
            user_id=user.id,
            role="member",
        )

        db.add(member)
        db.commit()
        db.refresh(member)

        member.full_name = user.full_name

        return member

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_group_members_group_user":
            raise HTTPException(
                status_code=409,
                detail="User is already a group member",
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise


def get_group_members(
    db: Session,
    group_id: int,
    requester_id: int,
) -> list[GroupMember]:
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Group not found",
        )

    requester = get_membership(
        db,
        group_id,
        requester_id,
    )

    if requester is None:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    statement = (
        select(GroupMember, User.full_name)
        .join(
            User,
            User.id == GroupMember.user_id,
        )
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.id)
    )

    members = []

    for member, full_name in db.execute(statement).all():
        member.full_name = full_name
        members.append(member)

    return members


def remove_group_member(
    db: Session,
    group_id: int,
    user_id: int,
    requester_id: int,
) -> None:
    try:
        lock_group(db, group_id)

        requester = get_membership(
            db,
            group_id,
            requester_id,
        )

        if requester is None or requester.role != "owner":
            raise HTTPException(
                status_code=403,
                detail="Only group owners can remove members",
            )

        member = get_membership(
            db,
            group_id,
            user_id,
        )

        if member is None:
            raise HTTPException(
                status_code=404,
                detail="Group member not found",
            )

        if member.role == "owner":
            raise HTTPException(
                status_code=409,
                detail="The group owner cannot be removed",
            )

        paid_expense = db.scalar(
            select(Expense.id)
            .where(
                Expense.group_id == group_id,
                Expense.paid_by == user_id,
            )
            .limit(1)
        )

        participated_expense = db.scalar(
            select(ExpenseSplit.id)
            .join(
                Expense,
                Expense.id == ExpenseSplit.expense_id,
            )
            .where(
                Expense.group_id == group_id,
                ExpenseSplit.user_id == user_id,
            )
            .limit(1)
        )

        payment = db.scalar(
            select(Payment.id)
            .where(
                Payment.group_id == group_id,
                or_(
                    Payment.from_user_id == user_id,
                    Payment.to_user_id == user_id,
                ),
            )
            .limit(1)
        )

        payment_request = db.scalar(
            select(PaymentRequest.id)
            .where(
                PaymentRequest.group_id == group_id,
                or_(
                    PaymentRequest.requester_id == user_id,
                    PaymentRequest.debtor_id == user_id,
                ),
            )
            .limit(1)
        )

        if any(
            record is not None
            for record in (
                paid_expense,
                participated_expense,
                payment,
                payment_request,
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cannot remove a member with "
                    "existing financial history"
                ),
            )

        db.delete(member)
        db.commit()

    except Exception:
        db.rollback()
        raise

def update_group(
    db: Session,
    group_id: int,
    requester_id: int,
    payload: GroupUpdate,
) -> Group:

    try:
        group = lock_group(db, group_id)

        requester = get_membership(
            db,
            group_id,
            requester_id,
        )

        if requester is None or requester.role != "owner":
            raise HTTPException(
                status_code=403,
                detail="Only group owners can edit groups",
            )

        group.name = payload.name
        group.category = payload.category
        group.custom_category = payload.custom_category

        db.commit()
        db.refresh(group)

        return group

    except Exception:
        db.rollback()
        raise