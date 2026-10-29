
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.core.security import hash_password


def test_create_group_assigns_owner(client, db_session):
    # Create a test user.
    user = User(
        full_name="Group Test User",
        email="group_test@example.com",
        hashed_password=hash_password("TestPassword123!"),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Log in to obtain a JWT.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "group_test@example.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # Create a group using the authenticated user.
    response = client.post(
        "/groups",
        json={"name": "Test Roommates"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201

    group_data = response.json()

    assert group_data["name"] == "Test Roommates"
    assert group_data["created_by"] == user.id

    # Verify the owner membership in PostgreSQL.
    group = db_session.get(Group, group_data["id"])

    assert group is not None

    member = (
        db_session.query(GroupMember)
        .filter_by(
            group_id=group.id,
            user_id=user.id,
        )
        .one()
    )

    assert member.role == "owner"




def test_list_user_groups(client, db_session):
    # Create a test user.
    user = User(
        full_name="List Test User",
        email="list_test@example.com",
        hashed_password=hash_password("TestPassword123!"),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Log in.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "list_test@example.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a group.
    create_response = client.post(
        "/groups",
        json={"name": "List Test Group"},
        headers=headers,
    )

    assert create_response.status_code == 201

    # Retrieve the user's groups.
    response = client.get("/groups", headers=headers)

    assert response.status_code == 200

    groups = response.json()

    assert len(groups) == 1
    assert groups[0]["name"] == "List Test Group"
    assert groups[0]["created_by"] == user.id




def test_user_cannot_see_other_users_groups(client):
    # Register two separate users.
    users = [
        ("Owner User", "privacy_owner@example.com"),
        ("Other User", "privacy_other@example.com"),
    ]

    tokens = []

    for full_name, email in users:
        register_response = client.post(
            "/auth/register",
            json={
                "full_name": full_name,
                "email": email,
                "password": "TestPassword123!",
            },
        )

        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "TestPassword123!",
            },
        )

        assert login_response.status_code == 200
        tokens.append(login_response.json()["access_token"])

    owner_headers = {
        "Authorization": f"Bearer {tokens[0]}"
    }
    other_headers = {
        "Authorization": f"Bearer {tokens[1]}"
    }

    # User 1 creates a private group.
    create_response = client.post(
        "/groups",
        json={"name": "Owner Private Group"},
        headers=owner_headers,
    )

    assert create_response.status_code == 201

    # User 1 can see their group.
    owner_response = client.get(
        "/groups",
        headers=owner_headers,
    )

    assert owner_response.status_code == 200
    assert len(owner_response.json()) == 1

    # User 2 must not see User 1's group.
    other_response = client.get(
        "/groups",
        headers=other_headers,
    )

    assert other_response.status_code == 200
    assert other_response.json() == []





def test_owner_can_add_group_member(client, db_session):
    password = "TestPassword123!"

    # Register the owner and a second user.
    for name, email in [
        ("Group Owner", "add_owner@example.com"),
        ("New Member", "add_member@example.com"),
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

    # Log in as the owner.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "add_owner@example.com",
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a group.
    create_response = client.post(
        "/groups",
        json={"name": "Membership Test Group"},
        headers=headers,
    )
    assert create_response.status_code == 201

    group_id = create_response.json()["id"]

    # Find the second user's database ID.
    member_user = (
        db_session.query(User)
        .filter_by(email="add_member@example.com")
        .one()
    )

    # Owner adds the second user.
    response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": member_user.id},
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["group_id"] == group_id
    assert data["user_id"] == member_user.id
    assert data["role"] == "member"

    # Verify the membership was saved in PostgreSQL.
    membership = (
        db_session.query(GroupMember)
        .filter_by(
            group_id=group_id,
            user_id=member_user.id,
        )
        .one()
    )

    assert membership.role == "member"




def test_regular_member_cannot_add_group_member(client):
    password = "TestPassword123!"

    # Register owner and regular member.
    user_ids = []

    for name, email in [
        ("Permission Owner", "permission_owner@example.com"),
        ("Permission Member", "permission_member@example.com"),
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
        user_ids.append(response.json()["id"])

    # Obtain JWT tokens for both users.
    tokens = []

    for email in [
        "permission_owner@example.com",
        "permission_member@example.com",
    ]:
        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 200
        tokens.append(response.json()["access_token"])

    owner_headers = {
        "Authorization": f"Bearer {tokens[0]}"
    }

    member_headers = {
        "Authorization": f"Bearer {tokens[1]}"
    }

    # Owner creates the group.
    group_response = client.post(
        "/groups",
        json={"name": "Permission Test Group"},
        headers=owner_headers,
    )

    assert group_response.status_code == 201

    group_id = group_response.json()["id"]

    # Owner adds the second user as a regular member.
    add_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": user_ids[1]},
        headers=owner_headers,
    )

    assert add_response.status_code == 201

    # Regular member attempts to add a user.
    # Owner is already in the group, but authorization
    # must be checked before duplicate membership.
    response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": user_ids[0]},
        headers=member_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Only group owners can add members"
    )




def test_cannot_add_duplicate_group_member(client):
    password = "TestPassword123!"

    # Register an owner and another user.
    user_ids = []

    for name, email in [
        ("Duplicate Owner", "duplicate_owner@example.com"),
        ("Duplicate Member", "duplicate_member@example.com"),
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
        user_ids.append(response.json()["id"])

    # Log in as the owner.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "duplicate_owner@example.com",
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
        json={"name": "Duplicate Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Add the member for the first time.
    first_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": user_ids[1]},
        headers=headers,
    )

    assert first_response.status_code == 201

    # Attempt to add the same member again.
    duplicate_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": user_ids[1]},
        headers=headers,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "User is already a group member"
    )




def test_cannot_add_nonexistent_user(client):
    password = "TestPassword123!"

    # Register the group owner.
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Missing User Test Owner",
            "email": "missing_user_owner@example.com",
            "password": password,
        },
    )

    assert register_response.status_code == 201

    # Log in as the owner.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "missing_user_owner@example.com",
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a group.
    group_response = client.post(
        "/groups",
        json={"name": "Missing User Test Group"},
        headers=headers,
    )

    assert group_response.status_code == 201

    group_id = group_response.json()["id"]

    # Attempt to add a nonexistent user.
    response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": 999999999},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"



def test_outsider_cannot_view_group_members(client):
    password = "TestPassword123!"

    # Register the group owner and an outsider.
    for name, email in [
        ("Privacy Owner", "members_owner@example.com"),
        ("Privacy Outsider", "members_outsider@example.com"),
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

    # Log in as both users.
    tokens = {}

    for email in [
        "members_owner@example.com",
        "members_outsider@example.com",
    ]:
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200
        tokens[email] = response.json()["access_token"]

    owner_headers = {
        "Authorization": f"Bearer {tokens['members_owner@example.com']}"
    }
    outsider_headers = {
        "Authorization": f"Bearer {tokens['members_outsider@example.com']}"
    }

    # Owner creates a group.
    response = client.post(
        "/groups",
        json={"name": "Private Membership Group"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    group_id = response.json()["id"]

    # Owner can view the membership list.
    owner_response = client.get(
        f"/groups/{group_id}/members",
        headers=owner_headers,
    )
    assert owner_response.status_code == 200
    assert len(owner_response.json()) == 1
    assert owner_response.json()[0]["role"] == "owner"

    # Outsider must not see the membership list.
    outsider_response = client.get(
        f"/groups/{group_id}/members",
        headers=outsider_headers,
    )

    assert outsider_response.status_code == 403
    assert outsider_response.json()["detail"] == (
        "You are not a member of this group"
    )




def test_regular_member_can_view_group_members(client):
    password = "TestPassword123!"

    # Register two users.
    users = {}

    for name, email in [
        ("View Owner", "view_owner@example.com"),
        ("View Member", "view_member@example.com"),
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
        "Authorization": f"Bearer {tokens['view_owner@example.com']}"
    }

    member_headers = {
        "Authorization": f"Bearer {tokens['view_member@example.com']}"
    }

    # Owner creates a group.
    group_response = client.post(
        "/groups",
        json={"name": "Member View Test Group"},
        headers=owner_headers,
    )

    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Owner adds the regular member.
    add_response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": users["view_member@example.com"]},
        headers=owner_headers,
    )

    assert add_response.status_code == 201

    # Regular member retrieves the group membership list.
    response = client.get(
        f"/groups/{group_id}/members",
        headers=member_headers,
    )

    assert response.status_code == 200

    members = response.json()

    assert len(members) == 2

    roles = {member["role"] for member in members}

    assert roles == {"owner", "member"}
