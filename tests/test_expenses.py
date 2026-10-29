
from decimal import Decimal


def test_create_expense_successfully(client, db_session):
    password = "TestPassword123!"

    # 1. Register two users.
    users = {}

    for name, email in [
        ("Expense Owner", "expense_owner@example.com"),
        ("Expense Member", "expense_member@example.com"),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201
        users[email] = response.json()["id"]

    # 2. Log in as the owner.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "expense_owner@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    owner_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # 3. Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Expense Test Group"},
        headers=owner_headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # 4. Add the second user.
    add_response = client.post(
        f"/groups/{group_id}/members",
        json={
            "user_id": users["expense_member@example.com"]
        },
        headers=owner_headers,
    )

    assert add_response.status_code == 201

    # 5. Create a shared expense.
    expense_response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Groceries",
            "amount": "100.00",
            "splits": [
                {
                    "user_id": users["expense_owner@example.com"],
                    "amount_owed": "50.00",
                },
                {
                    "user_id": users["expense_member@example.com"],
                    "amount_owed": "50.00",
                },
            ],
        },
        headers=owner_headers,
    )

    # 6. Verify the API response.
    assert expense_response.status_code == 201

    data = expense_response.json()

    assert data["group_id"] == group_id
    assert data["paid_by"] == users["expense_owner@example.com"]
    assert data["description"] == "Groceries"
    assert Decimal(data["amount"]) == Decimal("100.00")
    assert len(data["splits"]) == 2

    split_amounts = {
        split["user_id"]: Decimal(split["amount_owed"])
        for split in data["splits"]
    }

    assert split_amounts == {
        users["expense_owner@example.com"]: Decimal("50.00"),
        users["expense_member@example.com"]: Decimal("50.00"),
    }

    # 7. Verify the database records.
    from app.models.expense import Expense
    from app.models.expense_split import ExpenseSplit
    from sqlalchemy import select

    expense = db_session.get(Expense, data["id"])

    assert expense is not None
    assert expense.amount == Decimal("100.00")

    saved_splits = db_session.scalars(
        select(ExpenseSplit).where(
            ExpenseSplit.expense_id == expense.id
        )
    ).all()

    assert len(saved_splits) == 2
    assert sum(
        (split.amount_owed for split in saved_splits),
        Decimal("0.00"),
    ) == Decimal("100.00")





def test_reject_expense_when_splits_do_not_match_total(
    client,
    db_session,
):
    from sqlalchemy import select, func

    from app.models.expense import Expense
    from app.models.expense_split import ExpenseSplit

    password = "TestPassword123!"

    # Register two users.
    user_ids = {}

    for name, email in [
        ("Invalid Split Owner", "invalid_owner@example.com"),
        ("Invalid Split Member", "invalid_member@example.com"),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201
        user_ids[email] = response.json()["id"]

    # Authenticate as the group owner.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "invalid_owner@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Invalid Split Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Add the second participant.
    add_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": user_ids["invalid_member@example.com"]},
        headers=headers,
    )

    assert add_response.status_code == 201

    # Count existing records before the invalid request.
    expenses_before = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_before = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    # Attempt to create a $100 expense with only $90 in shares.
    response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Invalid Groceries",
            "amount": "100.00",
            "splits": [
                {
                    "user_id": user_ids["invalid_owner@example.com"],
                    "amount_owed": "40.00",
                },
                {
                    "user_id": user_ids["invalid_member@example.com"],
                    "amount_owed": "50.00",
                },
            ],
        },
        headers=headers,
    )

    # The API must reject the invalid total.
    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Expense splits must equal the total amount"
    )

    # No new expense or split records should exist.
    expenses_after = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_after = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    assert expenses_after == expenses_before
    assert splits_after == splits_before




def test_reject_duplicate_expense_participants(
    client,
    db_session,
):
    from sqlalchemy import select, func

    from app.models.expense import Expense
    from app.models.expense_split import ExpenseSplit

    password = "TestPassword123!"

    # Register the user.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Duplicate Test Owner",
            "email": "duplicate_expense_owner@example.com",
            "password": password,
        },
    )

    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    # Authenticate.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "duplicate_expense_owner@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Duplicate Expense Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Record database counts before the request.
    expenses_before = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_before = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    # Attempt to include the same participant twice.
    response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Groceries",
            "amount": "100.00",
            "splits": [
                {
                    "user_id": user_id,
                    "amount_owed": "50.00",
                },
                {
                    "user_id": user_id,
                    "amount_owed": "50.00",
                },
            ],
        },
        headers=headers,
    )

    # Duplicate participants must be rejected.
    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Duplicate users in expense splits"
    )

    # The database must remain unchanged.
    expenses_after = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_after = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    assert expenses_after == expenses_before
    assert splits_after == splits_before




def test_outsider_cannot_create_expense(client, db_session):
    from sqlalchemy import select, func

    from app.models.expense import Expense
    from app.models.expense_split import ExpenseSplit

    password = "TestPassword123!"

    # Register a group owner and an outsider.
    users = {}

    for name, email in [
        ("Expense Group Owner", "outsider_test_owner@example.com"),
        ("Expense Outsider", "outsider_test_user@example.com"),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201
        users[email] = response.json()["id"]

    # Log in as both users.
    tokens = {}

    for email in users:
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )

        assert response.status_code == 200
        tokens[email] = response.json()["access_token"]

    owner_headers = {
        "Authorization": f"Bearer {tokens['outsider_test_owner@example.com']}"
    }

    outsider_headers = {
        "Authorization": f"Bearer {tokens['outsider_test_user@example.com']}"
    }

    # Owner creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Private Expense Group"},
        headers=owner_headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Record database counts before the request.
    expenses_before = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_before = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    # Outsider attempts to create an expense.
    response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Unauthorized Groceries",
            "amount": "100.00",
            "splits": [
                {
                    "user_id": users["outsider_test_owner@example.com"],
                    "amount_owed": "100.00",
                }
            ],
        },
        headers=outsider_headers,
    )

    # Outsiders must not create group expenses.
    assert response.status_code == 403

    assert response.json()["detail"] == (
        "You are not a member of this group"
    )

    # No expense or split records should be saved.
    expenses_after = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_after = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    assert expenses_after == expenses_before
    assert splits_after == splits_before




def test_reject_expense_participant_outside_group(
    client,
    db_session,
):
    from sqlalchemy import select, func

    from app.models.expense import Expense
    from app.models.expense_split import ExpenseSplit

    password = "TestPassword123!"

    # Register the owner and an outsider.
    users = {}

    for name, email in [
        ("Participant Test Owner", "participant_owner@example.com"),
        ("Outside Participant", "outside_participant@example.com"),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201
        users[email] = response.json()["id"]

    # Log in as the owner.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "participant_owner@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a group containing only the owner.
    group_response = client.post(
        "/groups",
        json={"name": "Participant Validation Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Record database counts before the request.
    expenses_before = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_before = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    # Attempt to assign an expense share to an outsider.
    response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Invalid Participant Expense",
            "amount": "100.00",
            "splits": [
                {
                    "user_id": users["participant_owner@example.com"],
                    "amount_owed": "50.00",
                },
                {
                    "user_id": users["outside_participant@example.com"],
                    "amount_owed": "50.00",
                },
            ],
        },
        headers=headers,
    )

    # The outsider cannot be included in expense splits.
    assert response.status_code == 400

    assert response.json()["detail"] == (
        "All expense participants must be group members"
    )

    # Verify no financial records were created.
    expenses_after = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_after = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    assert expenses_after == expenses_before
    assert splits_after == splits_before





def test_outsider_cannot_view_group_expenses(client):
    password = "TestPassword123!"

    # Register the group owner and outsider.
    users = {}

    for name, email in [
        ("History Owner", "history_owner@example.com"),
        ("History Outsider", "history_outsider@example.com"),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201
        users[email] = response.json()["id"]

    # Authenticate both users.
    tokens = {}

    for email in users:
        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 200
        tokens[email] = response.json()["access_token"]

    owner_headers = {
        "Authorization": (
            f"Bearer {tokens['history_owner@example.com']}"
        )
    }

    outsider_headers = {
        "Authorization": (
            f"Bearer {tokens['history_outsider@example.com']}"
        )
    }

    # Owner creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Private Expense History Group"},
        headers=owner_headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Owner creates an expense.
    expense_response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Private Groceries",
            "amount": "80.00",
            "splits": [
                {
                    "user_id": users["history_owner@example.com"],
                    "amount_owed": "80.00",
                }
            ],
        },
        headers=owner_headers,
    )

    assert expense_response.status_code == 201

    # Owner can retrieve the expense history.
    owner_response = client.get(
        f"/groups/{group_id}/expenses",
        headers=owner_headers,
    )

    assert owner_response.status_code == 200
    assert len(owner_response.json()) == 1
    assert owner_response.json()[0]["description"] == (
        "Private Groceries"
    )

    # Outsider must not view the expense history.
    outsider_response = client.get(
        f"/groups/{group_id}/expenses",
        headers=outsider_headers,
    )

    assert outsider_response.status_code == 403
    assert outsider_response.json()["detail"] == (
        "You are not a member of this group"
    )




def test_regular_member_can_view_group_expenses(client):
    password = "TestPassword123!"

    # Register an owner and a regular member.
    users = {}

    for name, email in [
        ("Expense History Owner", "member_history_owner@example.com"),
        ("Expense History Member", "member_history_user@example.com"),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201
        users[email] = response.json()["id"]

    # Log in as both users.
    tokens = {}

    for email in users:
        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 200
        tokens[email] = response.json()["access_token"]

    owner_headers = {
        "Authorization": (
            f"Bearer {tokens['member_history_owner@example.com']}"
        )
    }

    member_headers = {
        "Authorization": (
            f"Bearer {tokens['member_history_user@example.com']}"
        )
    }

    # Owner creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Shared Expense History Group"},
        headers=owner_headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Owner adds the regular member.
    add_response = client.post(
        f"/groups/{group_id}/members",
        json={
            "user_id": users["member_history_user@example.com"]
        },
        headers=owner_headers,
    )

    assert add_response.status_code == 201

    # Owner records a shared expense.
    expense_response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Shared Dinner",
            "amount": "60.00",
            "splits": [
                {
                    "user_id": users["member_history_owner@example.com"],
                    "amount_owed": "30.00",
                },
                {
                    "user_id": users["member_history_user@example.com"],
                    "amount_owed": "30.00",
                },
            ],
        },
        headers=owner_headers,
    )

    assert expense_response.status_code == 201

    # Regular member retrieves expense history.
    response = client.get(
        f"/groups/{group_id}/expenses",
        headers=member_headers,
    )

    assert response.status_code == 200

    expenses = response.json()

    assert len(expenses) == 1
    assert expenses[0]["description"] == "Shared Dinner"
    assert expenses[0]["amount"] == "60.00"
    assert len(expenses[0]["splits"]) == 2







def test_reject_expense_with_more_than_two_decimal_places(client):
    password = "TestPassword123!"

    # Register a user.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Precision Test User",
            "email": "precision_test@example.com",
            "password": password,
        },
    )

    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    # Log in.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "precision_test@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Precision Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Submit an amount with three decimal places.
    response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Invalid Precision Expense",
            "amount": "25.555",
            "splits": [
                {
                    "user_id": user_id,
                    "amount_owed": "25.555",
                }
            ],
        },
        headers=headers,
    )

    # Pydantic must reject the invalid amount.
    assert response.status_code == 422





def test_reject_expense_with_blank_description(
    client,
    db_session,
):
    from sqlalchemy import select, func

    from app.models.expense import Expense
    from app.models.expense_split import ExpenseSplit

    password = "TestPassword123!"

    # Register a user.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Blank Description User",
            "email": "blank_description@example.com",
            "password": password,
        },
    )

    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    # Authenticate.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "blank_description@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Blank Description Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Count records before submitting the invalid expense.
    expenses_before = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_before = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    # Submit a whitespace-only description.
    response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "   ",
            "amount": "50.00",
            "splits": [
                {
                    "user_id": user_id,
                    "amount_owed": "50.00",
                }
            ],
        },
        headers=headers,
    )

    # Blank descriptions must be rejected.
    assert response.status_code == 422

    assert response.json()["detail"] == (
        "Expense description cannot be blank"
    )

    # Verify no expense or split records were saved.
    expenses_after = db_session.scalar(
        select(func.count()).select_from(Expense)
    )

    splits_after = db_session.scalar(
        select(func.count()).select_from(ExpenseSplit)
    )

    assert expenses_after == expenses_before
    assert splits_after == splits_before






def test_outsider_cannot_view_individual_expense(client):
    password = "TestPassword123!"

    # Register group owner and outsider.
    users = {}

    for name, email in [
        ("Detail Owner", "detail_owner@example.com"),
        ("Detail Outsider", "detail_outsider@example.com"),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201
        users[email] = response.json()["id"]

    # Authenticate both users.
    tokens = {}

    for email in users:
        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 200
        tokens[email] = response.json()["access_token"]

    owner_headers = {
        "Authorization": (
            f"Bearer {tokens['detail_owner@example.com']}"
        )
    }

    outsider_headers = {
        "Authorization": (
            f"Bearer {tokens['detail_outsider@example.com']}"
        )
    }

    # Owner creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Private Expense Details Group"},
        headers=owner_headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Owner creates an expense.
    expense_response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Private Dinner",
            "amount": "75.00",
            "splits": [
                {
                    "user_id": users["detail_owner@example.com"],
                    "amount_owed": "75.00",
                }
            ],
        },
        headers=owner_headers,
    )

    assert expense_response.status_code == 201
    expense_id = expense_response.json()["id"]

    # Owner can retrieve the expense.
    owner_response = client.get(
        f"/groups/{group_id}/expenses/{expense_id}",
        headers=owner_headers,
    )

    assert owner_response.status_code == 200
    assert owner_response.json()["description"] == "Private Dinner"

    # Outsider must not retrieve the expense.
    outsider_response = client.get(
        f"/groups/{group_id}/expenses/{expense_id}",
        headers=outsider_headers,
    )

    assert outsider_response.status_code == 403
    assert outsider_response.json()["detail"] == (
        "You are not a member of this group"
    )



def test_get_nonexistent_expense_returns_404(client):
    password = "TestPassword123!"

    # Register the group owner.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Missing Expense Test User",
            "email": "missing_expense@example.com",
            "password": password,
        },
    )

    assert register_response.status_code == 201

    # Authenticate.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "missing_expense@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Missing Expense Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Request an expense ID that does not exist.
    response = client.get(
        f"/groups/{group_id}/expenses/999999",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Expense not found"
    }




def test_cannot_access_expense_through_another_group(client):
    password = "TestPassword123!"

    # Register and authenticate the owner.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Cross Group Test User",
            "email": "cross_group_test@example.com",
            "password": password,
        },
    )

    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    login_response = client.post(
        "/auth/login",
        json={
            "email": "cross_group_test@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create two separate groups.
    group_ids = []

    for name in ["Group A", "Group B"]:
        response = client.post(
            "/groups",
            json={"name": name},
            headers=headers,
        )

        assert response.status_code == 201
        group_ids.append(response.json()["id"])

    group_a_id, group_b_id = group_ids

    # Create an expense in Group A.
    expense_response = client.post(
        f"/groups/{group_a_id}/expenses",
        json={
            "description": "Group A Groceries",
            "amount": "90.00",
            "splits": [
                {
                    "user_id": user_id,
                    "amount_owed": "90.00",
                }
            ],
        },
        headers=headers,
    )

    assert expense_response.status_code == 201
    expense_id = expense_response.json()["id"]

    # The expense must be accessible through Group A.
    correct_response = client.get(
        f"/groups/{group_a_id}/expenses/{expense_id}",
        headers=headers,
    )

    assert correct_response.status_code == 200

    # The same expense must not be accessible through Group B.
    wrong_group_response = client.get(
        f"/groups/{group_b_id}/expenses/{expense_id}",
        headers=headers,
    )

    assert wrong_group_response.status_code == 404
    assert wrong_group_response.json() == {
        "detail": "Expense not found"
    }



def test_new_group_has_empty_expense_history(client):
    password = "TestPassword123!"

    # Register a user.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Empty History User",
            "email": "empty_history@example.com",
            "password": password,
        },
    )

    assert register_response.status_code == 201

    # Authenticate.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "empty_history@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a group without any expenses.
    group_response = client.post(
        "/groups",
        json={"name": "Empty Expense Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Retrieve expense history.
    response = client.get(
        f"/groups/{group_id}/expenses",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []




def test_multiple_expenses_have_correct_splits(client):
    password = "TestPassword123!"

    users = {}
    tokens = {}

    # Register and authenticate two users.
    for name, email in [
        ("Multiple Expense Owner", "multi_owner@example.com"),
        ("Multiple Expense Member", "multi_member@example.com"),
    ]:
        register_response = client.post(
            "/auth/register",
            json={
                "full_name": name,
                "email": email,
                "password": password,
            },
        )

        assert register_response.status_code == 201
        users[email] = register_response.json()["id"]

        login_response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert login_response.status_code == 200
        tokens[email] = login_response.json()["access_token"]

    owner_id = users["multi_owner@example.com"]
    member_id = users["multi_member@example.com"]

    headers = {
        "Authorization": (
            f"Bearer {tokens['multi_owner@example.com']}"
        )
    }

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Multiple Expenses Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Add the second user to the group.
    member_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": member_id},
        headers=headers,
    )

    assert member_response.status_code == 201

    # Create two expenses with different splits.
    expense_cases = [
        {
            "description": "Groceries",
            "amount": "100.00",
            "splits": [
                {"user_id": owner_id, "amount_owed": "50.00"},
                {"user_id": member_id, "amount_owed": "50.00"},
            ],
        },
        {
            "description": "Electricity",
            "amount": "80.00",
            "splits": [
                {"user_id": owner_id, "amount_owed": "20.00"},
                {"user_id": member_id, "amount_owed": "60.00"},
            ],
        },
    ]

    for payload in expense_cases:
        response = client.post(
            f"/groups/{group_id}/expenses",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201

    # Retrieve all expenses.
    response = client.get(
        f"/groups/{group_id}/expenses",
        headers=headers,
    )

    assert response.status_code == 200

    expenses = response.json()
    assert len(expenses) == 2

    # Index by description so the test does not depend on order.
    by_description = {
        expense["description"]: expense
        for expense in expenses
    }

    assert set(by_description) == {"Groceries", "Electricity"}

    assert by_description["Groceries"]["amount"] == "100.00"
    assert by_description["Electricity"]["amount"] == "80.00"

    groceries_splits = {
        split["user_id"]: split["amount_owed"]
        for split in by_description["Groceries"]["splits"]
    }

    electricity_splits = {
        split["user_id"]: split["amount_owed"]
        for split in by_description["Electricity"]["splits"]
    }

    assert groceries_splits == {
        owner_id: "50.00",
        member_id: "50.00",
    }

    assert electricity_splits == {
        owner_id: "20.00",
        member_id: "60.00",
    }
