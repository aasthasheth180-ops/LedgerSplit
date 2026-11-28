from uuid import uuid4

from locust import HttpUser, task, between
from locust.exception import StopUser


class LedgerSplitUser(HttpUser):
    host = "http://localhost:8081"
    wait_time = between(1, 3)

    def on_start(self):
        if self.host.rstrip("/") != "http://localhost:8081":
            raise StopUser()

        self.email = f"load_{uuid4().hex}@example.com"
        self.password = "LoadTestPassword123!"

        self.client.headers.update({
            "Origin": "http://localhost:8081"
        })

        response = self.client.post(
            "/api/auth/register",
            json={
                "full_name": "Synthetic Load User",
                "email": self.email,
                "password": self.password,
            },
            name="POST /auth/register",
        )

        if response.status_code != 201:
            raise StopUser()

        self.user_id = response.json()["id"]

        response = self.client.post(
            "/api/auth/login",
            json={
                "email": self.email,
                "password": self.password,
                "remember_me": False,
            },
            name="POST /auth/login",
        )

        if response.status_code != 200:
            raise StopUser()

        token = response.json()["access_token"]

        self.client.headers.update({
            "Authorization": f"Bearer {token}"
        })

        response = self.client.post(
            "/api/groups",
            json={
                "name": "Load Test Group",
                "category": "Home",
                "currency": "USD",
                "default_split": "Equal",
            },
            headers={"Idempotency-Key": uuid4().hex},
            name="POST /groups",
        )

        if response.status_code != 201:
            raise StopUser()

        self.group_id = response.json()["id"]

    @task(3)
    def view_groups(self):
        self.client.get(
            "/api/groups",
            name="GET /groups",
        )

    @task(4)
    def view_balances(self):
        self.client.get(
            f"/api/groups/{self.group_id}/balances",
            name="GET /groups/:id/balances",
        )

    @task(3)
    def view_expenses(self):
        self.client.get(
            f"/api/groups/{self.group_id}/expenses",
            name="GET /groups/:id/expenses",
        )

    @task(2)
    def create_expense(self):
        self.client.post(
            f"/api/groups/{self.group_id}/expenses",
            json={
                "description": "Synthetic expense",
                "amount": "25.00",
                "category": "Groceries",
                "split_method": "Exact",
                "splits": [
                    {
                        "user_id": self.user_id,
                        "amount_owed": "25.00",
                    }
                ],
            },
            headers={"Idempotency-Key": uuid4().hex},
            name="POST /groups/:id/expenses",
        )

    @task(1)
    def view_profile(self):
        self.client.get(
            "/api/users/me",
            name="GET /users/me",
        )