from decimal import Decimal

def test_report_payment_requires_authentication(client):
    response = client.post(
        "/groups/1/payments",
        json={
            "to_user_id": 2,
            "amount": "30.00",
        },
    )

    assert response.status_code == 401


def test_group_member_can_report_payment(client, db_session):
    from app.models.payment import Payment

    # 1. Register Alice and Bob.
    alice_response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Payment API",
            "email": "payment_api_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_response.status_code == 201
    alice_id = alice_response.json()["id"]

    bob_response = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Payment API",
            "email": "payment_api_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_response.status_code == 201
    bob_id = bob_response.json()["id"]

    # 2. Alice logs in.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "payment_api_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    # 3. Alice creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Payment API Test Group"},
        headers=alice_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # 4. Alice adds Bob.
    member_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member_response.status_code == 201

    # 5. Bob logs in.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "payment_api_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}"
    }

    # 6. Bob reports paying Alice $30.
    response = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "30.00",
        },
        headers=bob_headers,
    )

    # 7. Verify API response.
    assert response.status_code == 201

    data = response.json()
    assert data["group_id"] == group_id
    assert data["from_user_id"] == bob_id
    assert data["to_user_id"] == alice_id
    assert data["amount"] == "30.00"
    assert data["status"] == "pending"
    assert data["confirmed_at"] is None
        # PostgreSQL must generate a creation timestamp.
    assert data["created_at"] is not None
    assert isinstance(data["created_at"], str)

    # 8. Verify PostgreSQL persistence.
    saved_payment = db_session.get(Payment, data["id"])

    assert saved_payment is not None
    assert saved_payment.from_user_id == bob_id
    assert saved_payment.to_user_id == alice_id
    assert saved_payment.status == "pending"


def test_nonmember_cannot_report_payment(client):
    # Register Alice, who will own the group.
    alice = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Payment Security",
            "email": "payment_security_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice.status_code == 201

    # Register Bob, who will remain outside the group.
    bob = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Payment Security",
            "email": "payment_security_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob.status_code == 201

    alice_login = client.post(
        "/auth/login",
        json={
            "email": "payment_security_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    group = client.post(
        "/groups",
        json={"name": "Private Payment Group"},
        headers=alice_headers,
    )
    assert group.status_code == 201

    bob_login = client.post(
        "/auth/login",
        json={
            "email": "payment_security_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}"
    }

    # Bob is authenticated but is not a member.
    response = client.post(
        f"/groups/{group.json()['id']}/payments",
        json={
            "to_user_id": alice.json()["id"],
            "amount": "30.00",
        },
        headers=bob_headers,
    )

    assert response.status_code == 403



def test_recipient_can_confirm_payment_via_api(client):
    # 1. Register Alice and Bob.
    alice = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Confirm API",
            "email": "confirm_api_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice.status_code == 201
    alice_id = alice.json()["id"]

    bob = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Confirm API",
            "email": "confirm_api_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob.status_code == 201
    bob_id = bob.json()["id"]

    # 2. Log in as Alice.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "confirm_api_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    # 3. Alice creates a group and adds Bob.
    group = client.post(
        "/groups",
        json={"name": "Payment Confirmation Group"},
        headers=alice_headers,
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    member = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member.status_code == 201


    # Create an expense so Bob owes Alice $50.
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

    assert expense_response.status_code == 201, expense_response.text


    # 4. Log in as Bob.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "confirm_api_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}",
        "Idempotency-Key": "confirm-payment-retry-001",
}

    # 5. Bob reports a $30 payment to Alice.
    reported = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "30.00",
        },
        headers=bob_headers,
    )

    assert reported.status_code == 201
    assert reported.json()["status"] == "pending"

    payment_id = reported.json()["id"]

    # 6. Alice confirms the payment.
    confirmed = client.post(
        f"/groups/{group_id}/payments/{payment_id}/confirm",
        headers=alice_headers,
    )

    assert confirmed.status_code == 200

    data = confirmed.json()

    assert data["id"] == payment_id
    assert data["from_user_id"] == bob_id
    assert data["to_user_id"] == alice_id
    assert data["amount"] == "30.00"
    assert data["status"] == "confirmed"
    assert data["confirmed_at"] is not None

        # Retry the original payment creation request after confirmation.
    retry = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "30.00",
        },
        headers=bob_headers,
    )

    assert retry.status_code == 201

    retry_data = retry.json()

    # The retry must return the original payment.
    assert retry_data["id"] == payment_id

    # The payment must remain confirmed.
    assert retry_data["status"] == "confirmed"

    # The original confirmation timestamp must remain unchanged.
    assert retry_data["confirmed_at"] == data["confirmed_at"]

    # Verify that the group still contains only one payment.
    history = client.get(
        f"/groups/{group_id}/payments",
        headers=bob_headers,
    )

    assert history.status_code == 200
    assert len(history.json()) == 1

    # 7. Confirming the same payment again must fail.
    duplicate = client.post(
        f"/groups/{group_id}/payments/{payment_id}/confirm",
        headers=alice_headers,
    )

    assert duplicate.status_code == 409


def test_recipient_can_reject_payment_via_api(client):
    # 1. Register Alice and Bob.
    alice = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Reject API",
            "email": "reject_api_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice.status_code == 201
    alice_id = alice.json()["id"]

    bob = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Reject API",
            "email": "reject_api_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob.status_code == 201
    bob_id = bob.json()["id"]

    # 2. Alice logs in.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "reject_api_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    # 3. Alice creates a group and adds Bob.
    group = client.post(
        "/groups",
        json={"name": "Payment Rejection Group"},
        headers=alice_headers,
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    member = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member.status_code == 201


    # Alice pays $100 for groceries, split equally.
    expense_response = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Groceries",
            "amount": "100.00",
            "splits": [
                {
                    "user_id": alice_id,
                    "amount_owed": "50.00",
                },
                {
                    "user_id": bob_id,
                    "amount_owed": "50.00",
                },
            ],
        },
        headers=alice_headers,
    )

    assert expense_response.status_code == 201


    # 4. Bob logs in.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "reject_api_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}",
        "Idempotency-Key": "reject-payment-retry-001",
}

    # 5. Bob reports paying Alice $30.
    reported = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "30.00",
        },
        headers=bob_headers,
    )

    assert reported.status_code == 201
    assert reported.json()["status"] == "pending"

    payment_id = reported.json()["id"]

    # 6. Alice rejects the payment.
    rejected = client.post(
        f"/groups/{group_id}/payments/{payment_id}/reject",
        headers=alice_headers,
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["confirmed_at"] is None

        # Retry the original payment request after rejection.
    retry = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "30.00",
        },
        headers=bob_headers,
    )

    assert retry.status_code == 201

    retry_data = retry.json()

    # The retry must return the original payment.
    assert retry_data["id"] == payment_id

    # The rejected payment must remain rejected.
    assert retry_data["status"] == "rejected"
    assert retry_data["confirmed_at"] is None

    # Verify that no duplicate payment was created.
    history = client.get(
        f"/groups/{group_id}/payments",
        headers=bob_headers,
    )

    assert history.status_code == 200
    assert len(history.json()) == 1

    # 7. A rejected payment cannot be confirmed.
    confirm_attempt = client.post(
        f"/groups/{group_id}/payments/{payment_id}/confirm",
        headers=alice_headers,
    )

    assert confirm_attempt.status_code == 409

    # 8. A rejected payment cannot be rejected again.
    duplicate_rejection = client.post(
        f"/groups/{group_id}/payments/{payment_id}/reject",
        headers=alice_headers,
    )

    assert duplicate_rejection.status_code == 409




def test_group_member_can_view_payment_history(client):
    # 1. Register Alice and Bob.
    alice = client.post(
        "/auth/register",
        json={
            "full_name": "Alice History",
            "email": "history_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice.status_code == 201
    alice_id = alice.json()["id"]

    bob = client.post(
        "/auth/register",
        json={
            "full_name": "Bob History",
            "email": "history_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob.status_code == 201
    bob_id = bob.json()["id"]

    # 2. Alice logs in.
    login = client.post(
        "/auth/login",
        json={
            "email": "history_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    # 3. Alice creates a group and adds Bob.
    group = client.post(
        "/groups",
        json={"name": "History Test Group"},
        headers=alice_headers,
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    member = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member.status_code == 201

    # 4. Verify that a new group has no payments.
    empty_history = client.get(
        f"/groups/{group_id}/payments",
        headers=alice_headers,
    )

    assert empty_history.status_code == 200
    assert empty_history.json() == []

    # 5. Bob logs in and reports a payment.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "history_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}"
    }

    reported = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "25.00",
        },
        headers=bob_headers,
    )
    assert reported.status_code == 201

    payment_id = reported.json()["id"]

    # 6. Alice retrieves the group's payment history.
    history = client.get(
        f"/groups/{group_id}/payments",
        headers=alice_headers,
    )

    assert history.status_code == 200

    payments = history.json()
    assert len(payments) == 1
    assert payments[0]["id"] == payment_id
    assert payments[0]["from_user_id"] == bob_id
    assert payments[0]["to_user_id"] == alice_id
    assert payments[0]["amount"] == "25.00"
    assert payments[0]["status"] == "pending"




def test_nonmember_cannot_view_payment_history(client):
    # Register Alice, who will own the group.
    alice = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Private History",
            "email": "private_history_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice.status_code == 201

    # Register Bob, who will not join the group.
    bob = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Private History",
            "email": "private_history_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob.status_code == 201

    # Alice logs in and creates a group.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "private_history_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    group = client.post(
        "/groups",
        json={"name": "Private Payment History"},
        headers=alice_headers,
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    # Bob logs in but remains outside Alice's group.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": "private_history_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}"
    }

    # Bob must not be allowed to access Alice's history.
    response = client.get(
        f"/groups/{group_id}/payments",
        headers=bob_headers,
    )

    assert response.status_code == 403



def test_payment_history_is_isolated_between_groups(client):
    # 1. Register Alice and Bob.
    alice = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Group Isolation",
            "email": "isolation_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice.status_code == 201
    alice_id = alice.json()["id"]

    bob = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Group Isolation",
            "email": "isolation_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob.status_code == 201
    bob_id = bob.json()["id"]

    # 2. Log in as Alice and Bob.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": "isolation_alice@example.com",
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200
    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    bob_login = client.post(
        "/auth/login",
        json={
            "email": "isolation_bob@example.com",
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200
    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}"
    }

    # 3. Alice creates two groups.
    group_a = client.post(
        "/groups",
        json={"name": "Isolation Group A"},
        headers=alice_headers,
    )
    group_b = client.post(
        "/groups",
        json={"name": "Isolation Group B"},
        headers=alice_headers,
    )

    assert group_a.status_code == 201
    assert group_b.status_code == 201

    group_a_id = group_a.json()["id"]
    group_b_id = group_b.json()["id"]

    # 4. Bob joins both groups.
    for group_id in (group_a_id, group_b_id):
        member = client.post(
            f"/groups/{group_id}/members",
            json={"user_id": bob_id},
            headers=alice_headers,
        )
        assert member.status_code == 201

    # 5. Bob reports a payment in Group A only.
    reported = client.post(
        f"/groups/{group_a_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "25.00",
        },
        headers=bob_headers,
    )
    assert reported.status_code == 201
    payment_id = reported.json()["id"]

    # 6. Alice retrieves both histories.
    history_a = client.get(
        f"/groups/{group_a_id}/payments",
        headers=alice_headers,
    )
    history_b = client.get(
        f"/groups/{group_b_id}/payments",
        headers=alice_headers,
    )

    assert history_a.status_code == 200
    assert history_b.status_code == 200

    # Group A contains the payment.
    assert len(history_a.json()) == 1
    assert history_a.json()[0]["id"] == payment_id

    # Group B must not contain Group A's payment.
    assert history_b.json() == []



def test_payment_history_contains_all_statuses(client):
    # Register Alice and Bob.
    users = {}

    for name in ("alice", "bob"):
        response = client.post(
            "/auth/register",
            json={
                "full_name": f"{name.title()} Status History",
                "email": f"status_history_{name}@example.com",
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 201
        users[name] = response.json()["id"]

    # Authenticate both users.
    headers = {}

    for name in ("alice", "bob"):
        response = client.post(
            "/auth/login",
            json={
                "email": f"status_history_{name}@example.com",
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 200
        headers[name] = {
            "Authorization": f"Bearer {response.json()['access_token']}"
        }

    # Alice creates a group and adds Bob.
    group = client.post(
        "/groups",
        json={"name": "Payment Status History"},
        headers=headers["alice"],
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    member = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": users["bob"]},
        headers=headers["alice"],
    )
    assert member.status_code == 201

    # Create an expense: Bob owes Alice $50.
    expense = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Groceries",
            "amount": "100.00",
            "splits": [
                {
                    "user_id": users["alice"],
                    "amount_owed": "50.00",
                },
                {
                    "user_id": users["bob"],
                    "amount_owed": "50.00",
                },
            ],
        },
        headers=headers["alice"],
    )
    assert expense.status_code == 201, expense.text

    payment_ids = {}

    # Create three pending payments.
    for label, amount in (
        ("confirmed", "30.00"),
        ("rejected", "10.00"),
        ("pending", "5.00"),
    ):
        response = client.post(
            f"/groups/{group_id}/payments",
            json={
                "to_user_id": users["alice"],
                "amount": amount,
            },
            headers=headers["bob"],
        )
        assert response.status_code == 201
        payment_ids[label] = response.json()["id"]

    # Alice confirms the $30 payment.
    confirmed = client.post(
        f"/groups/{group_id}/payments/"
        f"{payment_ids['confirmed']}/confirm",
        headers=headers["alice"],
    )
    assert confirmed.status_code == 200

    # Alice rejects the $10 payment.
    rejected = client.post(
        f"/groups/{group_id}/payments/"
        f"{payment_ids['rejected']}/reject",
        headers=headers["alice"],
    )
    assert rejected.status_code == 200

    # Retrieve payment history.
    history = client.get(
        f"/groups/{group_id}/payments",
        headers=headers["alice"],
    )
    assert history.status_code == 200

    payments = history.json()
    assert len(payments) == 3

    by_id = {payment["id"]: payment for payment in payments}

    assert by_id[payment_ids["confirmed"]]["status"] == "confirmed"
    assert by_id[payment_ids["rejected"]]["status"] == "rejected"
    assert by_id[payment_ids["pending"]]["status"] == "pending"

    assert by_id[payment_ids["confirmed"]]["confirmed_at"] is not None
    assert by_id[payment_ids["rejected"]]["confirmed_at"] is None
    assert by_id[payment_ids["pending"]]["confirmed_at"] is None

    # Newest first, with payment ID as timestamp tie-breaker.
    assert [p["id"] for p in payments] == sorted(
        payment_ids.values(),
        reverse=True,
    )



def test_payment_idempotency_same_key_returns_same_payment(
    client, db_session
):
    from uuid import uuid4
    from sqlalchemy import select, func
    from app.models.payment import Payment

    unique_id = uuid4().hex

    # 1. Register Alice and Bob with unique emails.
    alice_email = f"payment_idem_alice_{unique_id}@example.com"
    bob_email = f"payment_idem_bob_{unique_id}@example.com"

    alice_response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Idempotency",
            "email": alice_email,
            "password": "TestPassword123!",
        },
    )
    assert alice_response.status_code == 201
    alice_id = alice_response.json()["id"]

    bob_response = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Idempotency",
            "email": bob_email,
            "password": "TestPassword123!",
        },
    )
    assert bob_response.status_code == 201
    bob_id = bob_response.json()["id"]

    # 2. Alice logs in and creates a group.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": alice_email,
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    group_response = client.post(
        "/groups",
        json={"name": "Payment Idempotency Test Group"},
        headers=alice_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # 3. Add Bob to the group.
    member_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member_response.status_code == 201

    # 4. Bob logs in.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": bob_email,
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}",
        "Idempotency-Key": f"payment-{unique_id}",
    }

    payment_payload = {
        "to_user_id": alice_id,
        "amount": "30.00",
    }

    # 5. First request creates a payment.
    first_response = client.post(
        f"/groups/{group_id}/payments",
        json=payment_payload,
        headers=bob_headers,
    )

    assert first_response.status_code == 201
    first_payment_id = first_response.json()["id"]

    # 6. Retry with the same key and same payload.
    second_response = client.post(
        f"/groups/{group_id}/payments",
        json=payment_payload,
        headers=bob_headers,
    )

    assert second_response.status_code == 201
    second_payment_id = second_response.json()["id"]

    # 7. Both requests must return the same payment.
    assert first_payment_id == second_payment_id

    # 8. Verify only one payment was stored.
    payment_count = db_session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(Payment.group_id == group_id)
    )

    assert payment_count == 1

    saved_payment = db_session.get(Payment, first_payment_id)

    assert saved_payment is not None
    assert saved_payment.idempotency_key == bob_headers["Idempotency-Key"]
    assert saved_payment.status == "pending"



def test_payment_idempotency_same_key_different_amount_returns_409(
    client, db_session
):
    from uuid import uuid4
    from sqlalchemy import select, func
    from app.models.payment import Payment

    unique_id = uuid4().hex

    alice_email = f"payment_conflict_alice_{unique_id}@example.com"
    bob_email = f"payment_conflict_bob_{unique_id}@example.com"

    # 1. Register two users.
    alice_response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Payment Conflict",
            "email": alice_email,
            "password": "TestPassword123!",
        },
    )
    assert alice_response.status_code == 201
    alice_id = alice_response.json()["id"]

    bob_response = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Payment Conflict",
            "email": bob_email,
            "password": "TestPassword123!",
        },
    )
    assert bob_response.status_code == 201
    bob_id = bob_response.json()["id"]

    # 2. Alice logs in and creates a group.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": alice_email,
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    group_response = client.post(
        "/groups",
        json={"name": "Payment Conflict Test Group"},
        headers=alice_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    member_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member_response.status_code == 201

    # 3. Bob logs in.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": bob_email,
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    bob_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}",
        "Idempotency-Key": f"payment-conflict-{unique_id}",
    }

    # 4. First request: $30.
    first_response = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "30.00",
        },
        headers=bob_headers,
    )

    assert first_response.status_code == 201
    first_payment_id = first_response.json()["id"]

    # 5. Second request: same key, but $50.
    second_response = client.post(
        f"/groups/{group_id}/payments",
        json={
            "to_user_id": alice_id,
            "amount": "50.00",
        },
        headers=bob_headers,
    )

    # 6. The second request must be rejected.
    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"]
        == "Idempotency key already used for a different payment"
    )

    # 7. Verify that only the original payment exists.
    payment_count = db_session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(Payment.group_id == group_id)
    )

    assert payment_count == 1

    saved_payment = db_session.get(Payment, first_payment_id)

    assert saved_payment is not None
    assert saved_payment.amount == Decimal("30.00")


def test_payment_idempotency_different_keys_create_separate_payments(
    client, db_session
):
    from uuid import uuid4
    from sqlalchemy import select, func
    from app.models.payment import Payment

    unique_id = uuid4().hex

    alice_email = f"payment_keys_alice_{unique_id}@example.com"
    bob_email = f"payment_keys_bob_{unique_id}@example.com"

    # 1. Register Alice and Bob.
    alice_response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Different Keys",
            "email": alice_email,
            "password": "TestPassword123!",
        },
    )
    assert alice_response.status_code == 201
    alice_id = alice_response.json()["id"]

    bob_response = client.post(
        "/auth/register",
        json={
            "full_name": "Bob Different Keys",
            "email": bob_email,
            "password": "TestPassword123!",
        },
    )
    assert bob_response.status_code == 201
    bob_id = bob_response.json()["id"]

    # 2. Alice creates a group.
    alice_login = client.post(
        "/auth/login",
        json={
            "email": alice_email,
            "password": "TestPassword123!",
        },
    )
    assert alice_login.status_code == 200

    alice_headers = {
        "Authorization": f"Bearer {alice_login.json()['access_token']}"
    }

    group_response = client.post(
        "/groups",
        json={"name": "Different Payment Keys Group"},
        headers=alice_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    member_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": bob_id},
        headers=alice_headers,
    )
    assert member_response.status_code == 201

    # 3. Bob logs in.
    bob_login = client.post(
        "/auth/login",
        json={
            "email": bob_email,
            "password": "TestPassword123!",
        },
    )
    assert bob_login.status_code == 200

    base_headers = {
        "Authorization": f"Bearer {bob_login.json()['access_token']}"
    }

    payment_payload = {
        "to_user_id": alice_id,
        "amount": "30.00",
    }

    # 4. First payment uses key A.
    first_response = client.post(
        f"/groups/{group_id}/payments",
        json=payment_payload,
        headers={
            **base_headers,
            "Idempotency-Key": f"payment-A-{unique_id}",
        },
    )

    assert first_response.status_code == 201

    # 5. Second payment uses key B.
    second_response = client.post(
        f"/groups/{group_id}/payments",
        json=payment_payload,
        headers={
            **base_headers,
            "Idempotency-Key": f"payment-B-{unique_id}",
        },
    )

    assert second_response.status_code == 201

    # 6. Different keys must create different payments.
    first_payment_id = first_response.json()["id"]
    second_payment_id = second_response.json()["id"]

    assert first_payment_id != second_payment_id

    # 7. Verify that PostgreSQL contains two payments.
    payment_count = db_session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(Payment.group_id == group_id)
    )

    assert payment_count == 2
