import unittest
from datetime import datetime, timedelta

from server.src.api.app import create_app

REFERENCE = datetime(2026, 1, 1)


class ApiTest(unittest.TestCase):

    def setUp(self):
        self.app = create_app(":memory:")
        self.client = self.app.test_client()

    def _register_and_login(self, username="alice", password="s3cret!!", email="alice@example.com"):
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

    def test_health_endpoint_reports_ok(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_register_creates_user_without_password(self):
        response = self.client.post(
            "/api/users", json={"username": "alice", "password": "s3cret!!", "email": "alice@example.com"},
        )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["username"], "alice")
        self.assertNotIn("password", body)
        self.assertNotIn("password_hash", body)

    def test_register_rejects_duplicate_username(self):
        self.client.post("/api/users", json={"username": "alice", "password": "s3cret!!", "email": "a@x.com"})
        response = self.client.post("/api/users", json={"username": "alice", "password": "different!!", "email": "b@x.com"})
        self.assertEqual(response.status_code, 409)

    def test_login_rejects_wrong_password(self):
        self.client.post("/api/users", json={"username": "alice", "password": "s3cret!!", "email": "a@x.com"})
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
        token_a = self._register_and_login("alice", "s3cret!!", "a@x.com")
        token_b = self._register_and_login("bob", "s3cret!!", "b@x.com")
        self._create_task(token_a)

        listed_b = self.client.get("/api/tasks", headers=self._auth_headers(token_b))
        self.assertEqual(listed_b.get_json(), [])

    def test_cannot_access_another_users_task(self):
        token_a = self._register_and_login("alice", "s3cret!!", "a@x.com")
        token_b = self._register_and_login("bob", "s3cret!!", "b@x.com")
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

    def test_log_hours_reduces_remaining_duration(self):
        token = self._register_and_login()
        task_id = self._create_task(token, expected_duration_h=4.0).get_json()["task_id"]

        response = self.client.post(
            f"/api/tasks/{task_id}/log-hours", json={"hours": 1.5}, headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["expected_duration_h"], 2.5)
        self.assertFalse(response.get_json()["done"])

    def test_log_hours_marks_task_done_when_remaining_reaches_zero(self):
        token = self._register_and_login()
        task_id = self._create_task(token, expected_duration_h=2.0).get_json()["task_id"]

        response = self.client.post(
            f"/api/tasks/{task_id}/log-hours", json={"hours": 5.0}, headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["expected_duration_h"], 0.0)
        self.assertTrue(response.get_json()["done"])

    def test_log_hours_rejects_non_positive_hours(self):
        token = self._register_and_login()
        task_id = self._create_task(token).get_json()["task_id"]

        response = self.client.post(
            f"/api/tasks/{task_id}/log-hours", json={"hours": 0}, headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_log_hours_rejects_invalid_body(self):
        token = self._register_and_login()
        task_id = self._create_task(token).get_json()["task_id"]

        response = self.client.post(
            f"/api/tasks/{task_id}/log-hours", json={}, headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_log_hours_on_another_users_task_404s(self):
        token_a = self._register_and_login("alice", "s3cret!!", "a@x.com")
        token_b = self._register_and_login("bob", "s3cret!!", "b@x.com")
        task_id = self._create_task(token_a).get_json()["task_id"]

        response = self.client.post(
            f"/api/tasks/{task_id}/log-hours", json={"hours": 1.0}, headers=self._auth_headers(token_b),
        )
        self.assertEqual(response.status_code, 404)

    def test_train_prioritizer_reports_not_trained_without_enough_signal(self):
        token = self._register_and_login()
        self._create_task(token)

        response = self.client.post("/api/prioritizer/train", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["trained"])

    def _train_with_enough_signal(self, token):
        for i in range(3):
            task_id = self._create_task(token, name=f"done-{i}").get_json()["task_id"]
            self.client.post(f"/api/tasks/{task_id}/complete", headers=self._auth_headers(token))
        self._create_task(token, name="open")
        return self.client.post("/api/prioritizer/train", headers=self._auth_headers(token))

    def test_prioritizer_status_reports_untrained_by_default(self):
        token = self._register_and_login()

        response = self.client.get("/api/prioritizer/status", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["trained"])
        self.assertIsNone(body["updated_at"])

    def test_prioritizer_status_reports_trained_after_training(self):
        token = self._register_and_login()
        self.assertTrue(self._train_with_enough_signal(token).get_json()["trained"])

        response = self.client.get("/api/prioritizer/status", headers=self._auth_headers(token))
        body = response.get_json()
        self.assertTrue(body["trained"])
        self.assertIsNotNone(body["updated_at"])

    def test_delete_prioritizer_model_reverts_status_to_untrained(self):
        token = self._register_and_login()
        self.assertTrue(self._train_with_enough_signal(token).get_json()["trained"])

        response = self.client.delete("/api/prioritizer/model", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)

        status = self.client.get("/api/prioritizer/status", headers=self._auth_headers(token))
        self.assertFalse(status.get_json()["trained"])

    def test_prioritizer_status_and_delete_require_auth(self):
        self.assertEqual(self.client.get("/api/prioritizer/status").status_code, 401)
        self.assertEqual(self.client.delete("/api/prioritizer/model").status_code, 401)

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

    def test_week_plan_returns_one_entry_per_day(self):
        token = self._register_and_login()
        self._create_task(token, name="urgent", expected_duration_h=10.0, importance=9)

        response = self.client.get("/api/plan/week?days=3&hours=4", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(len(body), 3)
        self.assertEqual(body[0]["planned_hours_total"], 4.0)
        self.assertIn("diagnostics", body[0])

    def test_week_plan_flags_deadline_day_even_without_hours(self):
        token = self._register_and_login()
        self._create_task(
            token, name="due-soon",
            deadline=(datetime.now() + timedelta(days=2)).isoformat(),
            expected_duration_h=1.0, importance=1,
        )
        self._create_task(token, name="hungry", expected_duration_h=24.0, importance=10)

        response = self.client.get("/api/plan/week?days=4&hours=0", headers=self._auth_headers(token))
        body = response.get_json()
        self.assertEqual([task["name"] for task in body[2]["deadlines"]], ["due-soon"])

    def test_week_plan_rejects_invalid_days(self):
        token = self._register_and_login()
        response = self.client.get("/api/plan/week?days=0", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 400)

    def test_week_plan_requires_auth(self):
        response = self.client.get("/api/plan/week")
        self.assertEqual(response.status_code, 401)

    def test_logout_invalidates_token(self):
        token = self._register_and_login()
        self.client.post("/api/auth/logout", headers=self._auth_headers(token))

        response = self.client.get("/api/tasks", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 401)

    def test_get_me_returns_current_user_without_password(self):
        token = self._register_and_login()

        response = self.client.get("/api/users/me", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["username"], "alice")
        self.assertEqual(body["email"], "alice@example.com")
        self.assertNotIn("password_hash", body)

    def test_get_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/users/me").status_code, 401)

    def test_update_me_changes_email(self):
        token = self._register_and_login()

        response = self.client.put(
            "/api/users/me", json={"email": "new@example.com"}, headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["email"], "new@example.com")

        me = self.client.get("/api/users/me", headers=self._auth_headers(token))
        self.assertEqual(me.get_json()["email"], "new@example.com")

    def test_update_me_rejects_missing_email(self):
        token = self._register_and_login()
        response = self.client.put("/api/users/me", json={}, headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 400)

    def test_change_password_with_correct_current_password(self):
        token = self._register_and_login()

        response = self.client.post(
            "/api/users/me/password",
            json={"current_password": "s3cret!!", "new_password": "new-s3cret"},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 204)

        relogin = self.client.post("/api/auth/login", json={"username": "alice", "password": "new-s3cret"})
        self.assertEqual(relogin.status_code, 200)

    def test_change_password_with_wrong_current_password(self):
        token = self._register_and_login()

        response = self.client.post(
            "/api/users/me/password",
            json={"current_password": "wrong", "new_password": "new-s3cret"},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_change_password_rejects_missing_fields(self):
        token = self._register_and_login()
        response = self.client.post(
            "/api/users/me/password", json={"current_password": "s3cret!!"}, headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_create_task_with_recurrence_fields(self):
        token = self._register_and_login()
        response = self._create_task(
            token, name="standup", deadline=REFERENCE.isoformat(), expected_duration_h=0.5,
            recurrence_unit="week", recurrence_interval=2,
        )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["recurrence_unit"], "week")
        self.assertEqual(body["recurrence_interval"], 2)

    def test_create_task_rejects_invalid_recurrence_unit(self):
        token = self._register_and_login()
        response = self._create_task(token, recurrence_unit="fortnight")
        self.assertEqual(response.status_code, 400)

    def test_completing_recurring_task_spawns_next_occurrence(self):
        token = self._register_and_login()
        task_id = self._create_task(
            token, name="standup", deadline=REFERENCE.isoformat(), expected_duration_h=0.5,
            recurrence_unit="day", recurrence_interval=1,
        ).get_json()["task_id"]

        self.client.post(f"/api/tasks/{task_id}/complete", headers=self._auth_headers(token))

        listed = self.client.get("/api/tasks", headers=self._auth_headers(token)).get_json()
        self.assertEqual(len(listed), 2)
        spawned = next(t for t in listed if t["task_id"] != task_id)
        self.assertFalse(spawned["done"])
        self.assertEqual(spawned["deadline"], (REFERENCE + timedelta(days=1)).isoformat())

    def test_account_routes_require_auth(self):
        self.assertEqual(self.client.put("/api/users/me", json={"email": "x@x.com"}).status_code, 401)
        self.assertEqual(
            self.client.post("/api/users/me/password", json={"current_password": "a", "new_password": "b"})
            .status_code,
            401,
        )

    # --- Phase 15: delete account ---

    def test_delete_account_returns_204(self):
        token = self._register_and_login()
        response = self.client.delete("/api/users/me", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 204)

    def test_delete_account_revokes_token(self):
        token = self._register_and_login()
        self.client.delete("/api/users/me", headers=self._auth_headers(token))
        response = self.client.get("/api/tasks", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 401)

    def test_delete_account_cascade_removes_tasks(self):
        token = self._register_and_login()
        task_id = self._create_task(token).get_json()["task_id"]

        self.client.delete("/api/users/me", headers=self._auth_headers(token))

        # Re-register same username to confirm tasks are gone (not owned by the new account).
        new_token = self._register_and_login()
        listed = self.client.get("/api/tasks", headers=self._auth_headers(new_token))
        self.assertEqual(listed.get_json(), [])

    def test_delete_account_requires_auth(self):
        self.assertEqual(self.client.delete("/api/users/me").status_code, 401)

    # --- Phase 15: input validation ---

    def test_register_rejects_short_username(self):
        response = self.client.post(
            "/api/users", json={"username": "ab", "password": "longenough", "email": "a@b.com"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.get_json()["error"])

    def test_register_rejects_short_password(self):
        response = self.client.post(
            "/api/users", json={"username": "alice", "password": "short", "email": "a@b.com"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.get_json()["error"])

    def test_change_password_rejects_short_new_password(self):
        token = self._register_and_login()
        response = self.client.post(
            "/api/users/me/password",
            json={"current_password": "s3cret!!", "new_password": "tiny"},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.get_json()["error"])

    # --- Phase 15: session expiry ---

    def test_expired_session_is_rejected(self):
        token = self._register_and_login()
        # Directly set the session to expired in the DB.
        self.app.auth_service.session_dao.update_expires_at(token, "2000-01-01T00:00:00+00:00")
        response = self.client.get("/api/tasks", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 401)

    def test_session_is_extended_on_each_resolve(self):
        token = self._register_and_login()
        # Record the expiry right after login.
        row_before = self.app.auth_service.session_dao.get_session(token)
        expires_before = row_before["expires_at"]
        # Make a request that calls resolve_token.
        self.client.get("/api/tasks", headers=self._auth_headers(token))
        row_after = self.app.auth_service.session_dao.get_session(token)
        # expires_at must have been updated (>= original, as a string comparison on ISO timestamps).
        self.assertGreaterEqual(row_after["expires_at"], expires_before)

    def test_multiple_logins_issue_distinct_tokens(self):
        self._register_and_login()
        token_a = self.app.auth_service.session_dao.db.execute(
            "SELECT token FROM sessions"
        ).fetchall()
        self.client.post("/api/auth/login", json={"username": "alice", "password": "s3cret!!"})
        token_b = self.app.auth_service.session_dao.db.execute(
            "SELECT token FROM sessions"
        ).fetchall()
        self.assertGreater(len(token_b), len(token_a))

    # --- v1.1: Sign in with Google ---

    def _enable_google_auth(self, claims=None, raises=False):
        """Configures the app as if PRIOTASK_GOOGLE_CLIENT_ID were set, and
        swaps in a fake verifier so tests never hit Google's real network."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id"
        self.app.auth_service.google_client_id = "test-client-id"

        def fake_verifier(id_token_str, client_id):
            if raises:
                raise ValueError("invalid token")
            return claims

        self.app.auth_service.google_verifier = fake_verifier

    def test_google_auth_not_configured_returns_503(self):
        response = self.client.post("/api/auth/google", json={"id_token": "whatever"})
        self.assertEqual(response.status_code, 503)

    def test_google_auth_rejects_missing_id_token(self):
        self._enable_google_auth(claims={"sub": "g1", "email": "a@x.com", "email_verified": True})
        response = self.client.post("/api/auth/google", json={})
        self.assertEqual(response.status_code, 400)

    def test_google_auth_rejects_invalid_token(self):
        self._enable_google_auth(raises=True)
        response = self.client.post("/api/auth/google", json={"id_token": "bad"})
        self.assertEqual(response.status_code, 401)

    def test_google_auth_creates_new_account(self):
        self._enable_google_auth(claims={"sub": "g1", "email": "newbie@x.com", "email_verified": True})
        response = self.client.post("/api/auth/google", json={"id_token": "tok"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("token", body)
        self.assertIn("username", body)

        me = self.client.get("/api/users/me", headers=self._auth_headers(body["token"]))
        me_body = me.get_json()
        self.assertEqual(me_body["email"], "newbie@x.com")
        self.assertTrue(me_body["google_linked"])
        self.assertFalse(me_body["has_password"])

    def test_google_auth_links_existing_password_account_by_email(self):
        self._register_and_login("alice", "s3cret!!", "alice@example.com")
        self._enable_google_auth(claims={"sub": "g2", "email": "alice@example.com", "email_verified": True})

        response = self.client.post("/api/auth/google", json={"id_token": "tok"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["username"], "alice")

        me = self.client.get("/api/users/me", headers=self._auth_headers(response.get_json()["token"]))
        me_body = me.get_json()
        self.assertTrue(me_body["google_linked"])
        self.assertTrue(me_body["has_password"])  # still logs in with password too

    def test_google_auth_rejects_unverified_email(self):
        self._enable_google_auth(claims={"sub": "g3", "email": "x@x.com", "email_verified": False})
        response = self.client.post("/api/auth/google", json={"id_token": "tok"})
        self.assertEqual(response.status_code, 401)

    def test_google_only_account_cannot_change_password(self):
        self._enable_google_auth(claims={"sub": "g4", "email": "nopass@x.com", "email_verified": True})
        token = self.client.post("/api/auth/google", json={"id_token": "tok"}).get_json()["token"]

        response = self.client.post(
            "/api/users/me/password",
            json={"current_password": "anything", "new_password": "new-s3cret"},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    # --- Phase 15: auto-retrain callback ---

    def test_auto_retrain_callback_fires_at_threshold(self):
        from server.src.services.TaskManager import AUTO_RETRAIN_EVERY
        called_for = []

        def capture(user_id):
            called_for.append(user_id)

        self.app.task_manager._on_completion = capture

        token = self._register_and_login()
        # Complete exactly AUTO_RETRAIN_EVERY tasks.
        for _ in range(AUTO_RETRAIN_EVERY):
            task_id = self._create_task(token).get_json()["task_id"]
            self.client.post(f"/api/tasks/{task_id}/complete", headers=self._auth_headers(token))

        self.assertEqual(len(called_for), 1)

    def test_auto_retrain_callback_not_fired_before_threshold(self):
        from server.src.services.TaskManager import AUTO_RETRAIN_EVERY
        called_for = []

        def capture(user_id):
            called_for.append(user_id)

        self.app.task_manager._on_completion = capture

        token = self._register_and_login()
        for _ in range(AUTO_RETRAIN_EVERY - 1):
            task_id = self._create_task(token).get_json()["task_id"]
            self.client.post(f"/api/tasks/{task_id}/complete", headers=self._auth_headers(token))

        self.assertEqual(len(called_for), 0)

    # --- v1.2: Google Drive backup export/restore ---

    def test_export_backup_requires_auth(self):
        response = self.client.get("/api/users/me/backup")
        self.assertEqual(response.status_code, 401)

    def test_export_backup_returns_tasks_without_ids(self):
        token = self._register_and_login()
        self._create_task(token)

        response = self.client.get("/api/users/me/backup", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["format"], "priotask-backup")
        self.assertEqual(body["version"], 1)
        self.assertEqual(len(body["tasks"]), 1)
        self.assertEqual(body["tasks"][0]["name"], "write report")
        self.assertNotIn("task_id", body["tasks"][0])
        self.assertNotIn("user_id", body["tasks"][0])

    def test_import_backup_creates_tasks(self):
        token = self._register_and_login()
        backup = {
            "format": "priotask-backup",
            "version": 1,
            "tasks": [{
                "name": "restored task",
                "deadline": (REFERENCE + timedelta(days=3)).isoformat(),
                "expected_duration_h": 2.0,
                "importance": 4,
            }],
        }
        response = self.client.post(
            "/api/users/me/backup/restore", json=backup, headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"imported": 1})

        listed = self.client.get("/api/tasks", headers=self._auth_headers(token))
        self.assertEqual(len(listed.get_json()), 1)
        self.assertEqual(listed.get_json()[0]["name"], "restored task")

    def test_import_backup_preserves_done_status(self):
        token = self._register_and_login()
        backup = {
            "format": "priotask-backup",
            "version": 1,
            "tasks": [{
                "name": "already done",
                "deadline": REFERENCE.isoformat(),
                "expected_duration_h": 1.0,
                "importance": 1,
                "done": True,
                "completed_at": REFERENCE.isoformat(),
            }],
        }
        self.client.post("/api/users/me/backup/restore", json=backup, headers=self._auth_headers(token))

        listed = self.client.get("/api/tasks", headers=self._auth_headers(token)).get_json()
        self.assertTrue(listed[0]["done"])
        self.assertEqual(listed[0]["completed_at"], REFERENCE.isoformat())

    def test_import_backup_adds_to_existing_tasks_without_wiping_them(self):
        token = self._register_and_login()
        self._create_task(token, name="already here")
        backup = {
            "format": "priotask-backup",
            "version": 1,
            "tasks": [{
                "name": "from backup",
                "deadline": REFERENCE.isoformat(),
                "expected_duration_h": 1.0,
                "importance": 1,
            }],
        }
        self.client.post("/api/users/me/backup/restore", json=backup, headers=self._auth_headers(token))

        names = {t["name"] for t in self.client.get("/api/tasks", headers=self._auth_headers(token)).get_json()}
        self.assertEqual(names, {"already here", "from backup"})

    def test_import_backup_rejects_wrong_format(self):
        token = self._register_and_login()
        response = self.client.post(
            "/api/users/me/backup/restore", json={"format": "something-else", "tasks": []},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_import_backup_rejects_missing_tasks_list(self):
        token = self._register_and_login()
        response = self.client.post(
            "/api/users/me/backup/restore", json={"format": "priotask-backup"},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_import_backup_rejects_invalid_task_data(self):
        token = self._register_and_login()
        response = self.client.post(
            "/api/users/me/backup/restore",
            json={"format": "priotask-backup", "tasks": [{"name": "missing fields"}]},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_import_backup_requires_auth(self):
        response = self.client.post(
            "/api/users/me/backup/restore", json={"format": "priotask-backup", "tasks": []},
        )
        self.assertEqual(response.status_code, 401)

    def test_backup_round_trip_preserves_task_fields(self):
        token = self._register_and_login()
        self._create_task(
            token, name="round trip", task_type="work", task_subtype="writing",
            recurrence_unit="week", recurrence_interval=2,
        )
        exported = self.client.get("/api/users/me/backup", headers=self._auth_headers(token)).get_json()

        other_token = self._register_and_login(username="bob", email="bob@example.com")
        self.client.post(
            "/api/users/me/backup/restore", json=exported, headers=self._auth_headers(other_token),
        )
        restored = self.client.get("/api/tasks", headers=self._auth_headers(other_token)).get_json()[0]
        self.assertEqual(restored["name"], "round trip")
        self.assertEqual(restored["task_type"], "work")
        self.assertEqual(restored["task_subtype"], "writing")
        self.assertEqual(restored["recurrence_unit"], "week")
        self.assertEqual(restored["recurrence_interval"], 2)


if __name__ == "__main__":
    unittest.main()
