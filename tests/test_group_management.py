from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from app.core.security import hash_password
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.payment import Payment


PASSWORD = "TestPassword123!"


def create_user(db_session, name, active=True):
    user = User(
        full_name=name,
        email=f"{uuid4().hex}@example.com",
        hashed_password=hash_password(PASSWORD),
        is_active=active,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def login(client, user):
    response = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        )
    }


@pytest.fixture
def group_setup(client, db_session):
    owner = create_user(db_session, "Group Owner")
    member = create_user(db_session, "Group Member")
    outsider = create_user(db_session, "Outside User")

    headers = login(client, owner)

    response = client.post(
        "/groups",
        headers=headers,
        json={
            "name": "Test Group",
            "member_emails": [member.email],
        },
    )

    assert response.status_code == 201, response.text

    return {
        "owner": owner,
        "member": member,
        "outsider": outsider,
        "headers": headers,
        "group_id": response.json()["id"],
    }


def test_create_group_with_preferences(client, db_session):
    owner = create_user(db_session, "Owner")
    headers = login(client, owner)

    payload = {
        "name": "Research Team",
        "description": "Shared research expenses",
        "category": "Other",
        "custom_category": "Research",
        "currency": "EUR",
        "default_split": "Percent",
        "color": "#38627b",
    }

    response = client.post(
        "/groups",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    saved = db_session.get(Group, data["id"])

    for key, value in payload.items():
        assert data[key] == value
        assert getattr(saved, key) == value

    listed = client.get("/groups", headers=headers)

    assert listed.status_code == 200

    group = next(
        item for item in listed.json()
        if item["id"] == data["id"]
    )

    for key, value in payload.items():
        assert group[key] == value


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"name": "   "},
        {"category": "Invalid"},
        {"category": "Other"},
        {"category": "Other", "custom_category": "   "},
        {"category": "Home", "custom_category": "Research"},
        {"currency": "INVALID"},
        {"default_split": "Invalid"},
        {"color": "red"},
        {"description": "x" * 141},
        {"category": "Other", "custom_category": "x" * 51},
        {
            "member_emails": [
                "duplicate@example.com",
                "DUPLICATE@example.com",
            ]
        },
    ],
)
def test_invalid_group_preferences(
    client,
    db_session,
    invalid_fields,
):
    owner = create_user(db_session, "Owner")
    headers = login(client, owner)

    response = client.post(
        "/groups",
        headers=headers,
        json={
            "name": "Valid Group",
            **invalid_fields,
        },
    )

    assert response.status_code == 422, response.text


def test_initial_members_saved(
    client,
    db_session,
    group_setup,
):
    group_id = group_setup["group_id"]

    members = db_session.scalars(
        select(GroupMember).where(
            GroupMember.group_id == group_id
        )
    ).all()

    roles = {
        member.user_id: member.role
        for member in members
    }

    assert roles == {
        group_setup["owner"].id: "owner",
        group_setup["member"].id: "member",
    }

    member_headers = login(
        client,
        group_setup["member"],
    )

    response = client.get(
        "/groups",
        headers=member_headers,
    )

    assert response.status_code == 200

    assert group_id in [
        group["id"] for group in response.json()
    ]


@pytest.mark.parametrize(
    "invalid_member",
    ["missing", "inactive", "creator"],
)
def test_group_creation_is_atomic(
    client,
    db_session,
    invalid_member,
):
    owner = create_user(db_session, "Owner")
    valid = create_user(db_session, "Valid Member")
    inactive = create_user(
        db_session,
        "Inactive Member",
        active=False,
    )

    headers = login(client, owner)

    invalid_email = {
        "missing": f"{uuid4().hex}@example.com",
        "inactive": inactive.email,
        "creator": owner.email,
    }[invalid_member]

    before_groups = db_session.scalar(
        select(func.count()).select_from(Group)
    )

    before_members = db_session.scalar(
        select(func.count()).select_from(GroupMember)
    )

    response = client.post(
        "/groups",
        headers=headers,
        json={
            "name": "Atomic Group",
            "member_emails": [
                valid.email,
                invalid_email,
            ],
        },
    )

    expected = 400 if invalid_member == "creator" else 404

    assert response.status_code == expected

    assert db_session.scalar(
        select(func.count()).select_from(Group)
    ) == before_groups

    assert db_session.scalar(
        select(func.count()).select_from(GroupMember)
    ) == before_members


def test_add_member_by_email(
    client,
    db_session,
    group_setup,
):
    user = group_setup["outsider"]
    group_id = group_setup["group_id"]

    response = client.post(
        f"/groups/{group_id}/members",
        headers=group_setup["headers"],
        json={"email": user.email.upper()},
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["user_id"] == user.id
    assert data["role"] == "member"
    assert data["full_name"] == user.full_name

    duplicate = client.post(
        f"/groups/{group_id}/members",
        headers=group_setup["headers"],
        json={"email": user.email},
    )

    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"user_id": 1, "email": "test@example.com"},
        {"user_id": 0},
        {"email": "invalid-email"},
    ],
)
def test_invalid_member_identifier(
    client,
    group_setup,
    payload,
):
    group_id = group_setup["group_id"]

    response = client.post(
        f"/groups/{group_id}/members",
        headers=group_setup["headers"],
        json=payload,
    )

    assert response.status_code == 422


def test_member_names_and_privacy(client, group_setup):
    group_id = group_setup["group_id"]

    response = client.get(
        f"/groups/{group_id}/members",
        headers=group_setup["headers"],
    )

    assert response.status_code == 200

    members = response.json()

    assert {member["full_name"] for member in members} == {
        "Group Owner",
        "Group Member",
    }

    assert all(
        "email" not in member
        for member in members
    )


@pytest.mark.parametrize(
    "requester",
    ["member", "outsider"],
)
def test_unauthorized_email_addition(
    client,
    group_setup,
    requester,
):
    headers = login(client, group_setup[requester])
    group_id = group_setup["group_id"]

    response = client.post(
        f"/groups/{group_id}/members",
        headers=headers,
        json={
            "email": group_setup["outsider"].email
        },
    )

    assert response.status_code == 403


def test_remove_member_without_history(
    client,
    db_session,
    group_setup,
):
    group_id = group_setup["group_id"]
    member = group_setup["member"]

    response = client.delete(
        f"/groups/{group_id}/members/{member.id}",
        headers=group_setup["headers"],
    )

    assert response.status_code == 204

    saved = db_session.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == member.id,
        )
    )

    assert saved is None

    headers = login(client, member)

    groups = client.get("/groups", headers=headers)

    assert groups.status_code == 200

    assert group_id not in [
        group["id"] for group in groups.json()
    ]

    members = client.get(
        f"/groups/{group_id}/members",
        headers=headers,
    )

    assert members.status_code == 403


@pytest.mark.parametrize(
    "requester,target,expected",
    [
        ("member", "member", 403),
        ("outsider", "member", 403),
        ("owner", "owner", 409),
        ("owner", "outsider", 404),
    ],
)
def test_member_removal_restrictions(
    client,
    group_setup,
    requester,
    target,
    expected,
):
    headers = login(client, group_setup[requester])
    group_id = group_setup["group_id"]
    target_id = group_setup[target].id

    response = client.delete(
        f"/groups/{group_id}/members/{target_id}",
        headers=headers,
    )

    assert response.status_code == expected


@pytest.mark.parametrize(
    "history_type",
    [
        "expense_payer",
        "expense_participant",
        "payment_sender",
        "payment_recipient",
    ],
)
def test_cannot_remove_member_with_financial_history(
    client,
    db_session,
    group_setup,
    history_type,
):
    group_id = group_setup["group_id"]
    owner_id = group_setup["owner"].id
    member_id = group_setup["member"].id

    if history_type in (
        "expense_payer",
        "expense_participant",
    ):
        payer_id = (
            member_id
            if history_type == "expense_payer"
            else owner_id
        )

        expense = Expense(
            group_id=group_id,
            paid_by=payer_id,
            description="Shared expense",
            amount=Decimal("20.00"),
        )

        db_session.add(expense)
        db_session.flush()

        participant_id = (
            owner_id
            if history_type == "expense_payer"
            else member_id
        )

        db_session.add(
            ExpenseSplit(
                expense_id=expense.id,
                user_id=participant_id,
                amount_owed=Decimal("20.00"),
            )
        )

    else:
        sender_id = (
            member_id
            if history_type == "payment_sender"
            else owner_id
        )

        recipient_id = (
            owner_id
            if history_type == "payment_sender"
            else member_id
        )

        db_session.add(
            Payment(
                group_id=group_id,
                from_user_id=sender_id,
                to_user_id=recipient_id,
                amount=Decimal("10.00"),
                status="pending",
            )
        )

    db_session.commit()

    response = client.delete(
        f"/groups/{group_id}/members/{member_id}",
        headers=group_setup["headers"],
    )

    assert response.status_code == 409

    membership = db_session.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == member_id,
        )
    )

    assert membership is not None