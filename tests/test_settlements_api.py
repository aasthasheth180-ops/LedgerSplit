
def test_settlements_requires_authentication(client):
    response = client.get("/groups/1/settlements")

    assert response.status_code == 401

def test_nonmember_cannot_view_settlements(client):
    # Register the group owner.
    client.post(
        "/auth/register",
        json={
            "full_name": "Alice",
            "email": "alice123@example.com",
            "password": "Password123!",
        },
    )

    # Register another user.
    client.post(
        "/auth/register",
        json={
            "full_name": "Bob",
            "email": "bob123@example.com",
            "password": "Password123!",
        },
    )

    # Login as Alice.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "alice123@example.com",
            "password": "Password123!",
        },
    )
    assert alice_login.status_code == 200

    alice_token = alice_login.json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # Alice creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Apartment"},
        headers=alice_headers,
    )
    assert group_response.status_code in (200, 201)

    group_id = group_response.json()["id"]

    # Login as Bob, who is not a member.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "bob123@example.com",
            "password": "Password123!",
        },
    )
    assert bob_login.status_code == 200

    bob_token = bob_login.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    response = client.get(
        f"/groups/{group_id}/settlements",
        headers=bob_headers,
    )

    assert response.status_code == 403


def test_nonexistent_group_settlements(client):
    # Register and log in.
    client.post(
        "/auth/register",
        json={
            "full_name": "Charlie",
            "email": "charlie123@example.com",
            "password": "Password123!",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": "charlie123@example.com",
            "password": "Password123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/groups/999999/settlements",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404

def test_group_without_expenses_has_no_settlements(client):
    # Register Alice.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice",
            "email": "alice_empty@example.com",
            "password": "Password123!",
        },
    )
    assert register_response.status_code == 201

    # Login.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "alice_empty@example.com",
            "password": "Password123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Empty Apartment"},
        headers=headers,
    )
    assert group_response.status_code in (200, 201)

    group_id = group_response.json()["id"]

    # Request settlement suggestions.
    response = client.get(
        f"/groups/{group_id}/settlements",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "group_id": group_id,
        "settlements": [],
    }


def test_settlements_for_real_expense(client):
    users = {}

    # Register three roommates.
    for name in ["alice", "bob", "charlie"]:
        response = client.post(
            "/auth/register",
            json={
                "full_name": name.title(),
                "email": f"{name}_settlement@example.com",
                "password": "Password123!",
            },
        )
        assert response.status_code == 201
        users[name] = response.json()["id"]

    # Alice logs in.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "alice_settlement@example.com",
            "password": "Password123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Alice creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Roommate Expenses"},
        headers=headers,
    )
    assert group_response.status_code == 201

    group_id = group_response.json()["id"]

    # Add Bob and Charlie as group members.
    for name in ["bob", "charlie"]:
        response = client.post(
            f"/groups/{group_id}/members",
            json={"user_id": users[name]},
            headers=headers,
        )
        assert response.status_code in (200, 201)

    # Alice pays $90 for groceries.
    expense_response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Groceries",
            "amount": "90.00",
            "splits": [
                {
                    "user_id": users["alice"],
                    "amount_owed": "30.00",
                },
                {
                    "user_id": users["bob"],
                    "amount_owed": "30.00",
                },
                {
                    "user_id": users["charlie"],
                    "amount_owed": "30.00",
                },
            ],
        },
        headers=headers,
    )
    assert expense_response.status_code == 201

    # Request settlement suggestions.
    response = client.get(
        f"/groups/{group_id}/settlements",
        headers=headers,
    )

    assert response.status_code == 200

    assert response.json() == {
        "group_id": group_id,
        "settlements": [
            {
                "from_user_id": users["bob"],
                "to_user_id": users["alice"],
                "amount": "30.00",
            },
            {
                "from_user_id": users["charlie"],
                "to_user_id": users["alice"],
                "amount": "30.00",
            },
        ],
    }
