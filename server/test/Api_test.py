import unittest
from datetime import datetime, timedelta

from server.src.api.app import create_app

REFERENCE = datetime(2026, 1, 1)


class ApiTest(unittest.TestCase):

    def setUp(self):
        self.app = create_app(":memory:")
        self.client = self.app.test_client()

    def _register_and_login(self, username="alice", password="s3cret", email="alice@example.com"):
        self.client.post("/api/users", json={"username": username, "password": password, "email": email})
        response = self.client.post("/api/auth/login", json={"username": username, "password": password})
        return response.get_json()["token"]

    def _auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _create_task(self, token, **overrides):
        body = {
            "name": "write report",
            "deadline": (REFERENCE + timedelta(days=2)).isoformat(),
            "expected_duration_h": 4.0,
            "importance": 5,
        }
        body.update(overrides)
        return self.client.post("/api/tasks", json=body, headers=self._auth_headers(token))

    def test_register_creates_user_without_password(self):
        response = self.client.post(
            "/api/users", json={"username": "alice", "password": "s3cret", "email": "alice@example.com"},
        )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["username"], "alice")
        self.assertNotIn("password", body)
        self.assertNotIn("password_hash", body)

    def test_register_rejects_duplicate_username(self):
        self.client.post("/api/users", json={"username": "alice", "password": "s3cret", "email": "a@x.com"})
        response = self.client.post("/api/users", json={"username": "alice", "password": "other", "email": "b@x.com"})
        self.assertEqual(response.status_code, 409)

    def test_login_rejects_wrong_password(self):
        self.client.post("/api/users", json={"username": "alice", "password": "s3cret", "email": "a@x.com"})
        response = self.client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
        self.assertEqual(response.status_code, 401)

    def test_tasks_endpoint_requires_auth(self):
        response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code, 401)

    def test_create_and_list_tasks(self):
        token = self._register_and_login()
        created = self._create_task(token)
        self.assertEqual(created.status_code, 201)

        listed = self.client.get("/api/tasks", headers=self._auth_headers(token))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()), 1)
        self.assertEqual(listed.get_json()[0]["name"], "write report")

    def test_users_only_see_their_own_tasks(self):
        token_a = self._register_and_login("alice", "s3cret", "a@x.com")
        token_b = self._register_and_login("bob", "s3cret", "b@x.com")
        self._create_task(token_a)

        listed_b = self.client.get("/api/tasks", headers=self._auth_headers(token_b))
        self.assertEqual(listed_b.get_json(), [])

    def test_cannot_access_another_users_task(self):
        token_a = self._register_and_login("alice", "s3cret", "a@x.com")
        token_b = self._register_and_login("bob", "s3cret", "b@x.com")
        task_id = self._create_task(token_a).get_json()["task_id"]

        response = self.client.get(f"/api/tasks/{task_id}", headers=self._auth_headers(token_b))
        self.assertEqual(response.status_code, 404)

    def test_update_task(self):
        token = self._register_and_login()
        task_id = self._create_task(token).get_json()["task_id"]

        response = self.client.put(
            f"/api/tasks/{task_id}",
            json={
                "name": "final report", "deadline": REFERENCE.isoformat(),
                "expected_duration_h": 2.0, "importance": 9,
            },
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["name"], "final report")
        self.assertEqual(response.get_json()["importance"], 9)

    def test_complete_task_marks_it_done(self):
        token = self._register_and_login()
        task_id = self._create_task(token).get_json()["task_id"]

        response = self.client.post(f"/api/tasks/{task_id}/complete", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["done"])

    def test_delete_task_removes_it(self):
        token = self._register_and_login()
        task_id = self._create_task(token).get_json()["task_id"]

        response = self.client.delete(f"/api/tasks/{task_id}", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 204)

        response = self.client.get(f"/api/tasks/{task_id}", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 404)

    def test_today_plan_ranks_tasks_and_assigns_hours(self):
        token = self._register_and_login()
        self._create_task(
            token, name="urgent", deadline=(REFERENCE + timedelta(hours=12)).isoformat(),
            expected_duration_h=4.0, importance=9,
        )
        self._create_task(
            token, name="not urgent", deadline=(REFERENCE + timedelta(days=30)).isoformat(),
            expected_duration_h=4.0, importance=1,
        )

        response = self.client.get("/api/plan/today?hours=6", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(len(body), 2)
        self.assertEqual(body[0]["task"]["name"], "urgent")
        self.assertGreater(body[0]["recommended_hours_today"], body[1]["recommended_hours_today"])

    def test_logout_invalidates_token(self):
        token = self._register_and_login()
        self.client.post("/api/auth/logout", headers=self._auth_headers(token))

        response = self.client.get("/api/tasks", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
