from decimal import Decimal

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit

from app.services.ledger_service import calculate_group_balances

def test_balances_endpoint_requires_authentication(client):
    # Attempt to access balances without a JWT token.
    response = client.get("/groups/1/balances")

    # The request must be rejected.
    assert response.status_code == 401




def test_non_member_cannot_view_group_balances(client):
    # Register Alice.
    alice_response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Security",
            "email": "balances_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_response.status_code == 201

    # Register Bob.
    bob_response = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Security",
            "email": "balances_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_response.status_code == 201

    # Log in as Alice.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "balances_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": (
            f"Bearer {alice_login.json()['access_token']}"
        )
    }

    # Alice creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Alice Private Group"},
        headers=alice_headers,
    )
    assert group_response.status_code == 201

    group_id = group_response.json()["id"]

    # Log in as Bob.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "balances_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": (
            f"Bearer {bob_login.json()['access_token']}"
        )
    }

    # Bob tries to view Alice's group balances.
    response = client.get(
        f"/groups/{group_id}/balances",
        headers=bob_headers,
    )

    # Bob is authenticated but is not a group member.
    assert response.status_code == 403




def test_group_member_can_view_correct_balances(client):
    # Register Alice and Bob.
    alice_response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Balances",
            "email": "api_balances_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_response.status_code == 201
    alice_id = alice_response.json()["id"]

    bob_response = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Balances",
            "email": "api_balances_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_response.status_code == 201
    bob_id = bob_response.json()["id"]

    # Log in as Alice.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "api_balances_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    # Alice creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Balances API Test Group"},
        headers=alice_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Alice adds Bob to the group.
    member_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member_response.status_code == 201

    # Alice pays $100 for groceries.
    expense_response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Groceries",
            "amount": "100.00",
            "splits": [
                {"user_id": alice_id, "amount_owed": "50.00"},
                {"user_id": bob_id, "amount_owed": "50.00"},
            ],
        },
        headers=alice_headers,
    )
    assert expense_response.status_code == 201

    # Log in as Bob, who is a group member.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "api_balances_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}"
    }

    # Bob retrieves the group's balances.
    response = client.get(
        f"/groups/{group_id}/balances",
        headers=bob_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["group_id"] == group_id

    balances = {
        item["user_id"]: item["net_balance"]
        for item in data["balances"]
    }

    # Alice paid $100 but owes $50.
    assert balances[alice_id] == "50.00"

    # Bob paid nothing but owes $50.
    assert balances[bob_id] == "-50.00"

    assert len(balances) == 2




def test_balances_for_nonexistent_group_returns_404(client):
    # Register a user.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Missing Group Tester",
            "email": "missing_group_balances@example.com",
            "password": "TestPassword123!",
        },
    )
    assert register_response.status_code == 201

    # Log in to obtain a valid JWT.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "missing_group_balances@example.com",
            "password": "TestPassword123!",
        },
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Request a group ID that does not exist.
    response = client.get(
        "/groups/999999999/balances",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Group not found"





def test_group_balances_are_isolated(db_session):
    # Create three users.
    alice = User(
        full_name="Alice Isolation",
        email="isolation_alice@example.com",
        hashed_password="test_hash",
    )
    bob = User(
        full_name="Bob Isolation",
        email="isolation_bob@example.com",
        hashed_password="test_hash",
    )
    charlie = User(
        full_name="Charlie Isolation",
        email="isolation_charlie@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob, charlie])
    db_session.flush()

    # Alice creates two separate groups.
    group_a = Group(
        name="Isolation Group A",
        created_by=alice.id,
    )
    group_b = Group(
        name="Isolation Group B",
        created_by=alice.id,
    )

    db_session.add_all([group_a, group_b])
    db_session.flush()

    # Group A: Alice and Bob.
    # Group B: Alice and Charlie.
    db_session.add_all([
        GroupMember(
            group_id=group_a.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group_a.id,
            user_id=bob.id,
            role="member",
        ),
        GroupMember(
            group_id=group_b.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group_b.id,
            user_id=charlie.id,
            role="member",
        ),
    ])
    db_session.flush()

    # Alice pays $100 in Group A.
    expense_a = Expense(
        group_id=group_a.id,
        paid_by=alice.id,
        description="Group A Groceries",
        amount=Decimal("100.00"),
    )

    # Alice pays $80 in Group B.
    expense_b = Expense(
        group_id=group_b.id,
        paid_by=alice.id,
        description="Group B Dinner",
        amount=Decimal("80.00"),
    )

    db_session.add_all([expense_a, expense_b])
    db_session.flush()

    db_session.add_all([
        ExpenseSplit(
            expense_id=expense_a.id,
            user_id=alice.id,
            amount_owed=Decimal("50.00"),
        ),
        ExpenseSplit(
            expense_id=expense_a.id,
            user_id=bob.id,
            amount_owed=Decimal("50.00"),
        ),
        ExpenseSplit(
            expense_id=expense_b.id,
            user_id=alice.id,
            amount_owed=Decimal("40.00"),
        ),
        ExpenseSplit(
            expense_id=expense_b.id,
            user_id=charlie.id,
            amount_owed=Decimal("40.00"),
        ),
    ])
    db_session.flush()

    # Calculate each group independently.
    balances_a = calculate_group_balances(
        db=db_session,
        group_id=group_a.id,
    )
    balances_b = calculate_group_balances(
        db=db_session,
        group_id=group_b.id,
    )

    # Group A must contain only Alice and Bob.
    assert balances_a == {
        alice.id: Decimal("50.00"),
        bob.id: Decimal("-50.00"),
    }

    # Group B must contain only Alice and Charlie.
    assert balances_b == {
        alice.id: Decimal("40.00"),
        charlie.id: Decimal("-40.00"),
    }

    # Both groups must independently balance to zero.
    assert sum(balances_a.values()) == Decimal("0.00")
    assert sum(balances_b.values()) == Decimal("0.00")
