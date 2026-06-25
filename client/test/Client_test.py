'''
This is a test file for the client. It is used to test the client's
functionality.
'''
import unittest

from client.src.Client import create_app


class ClientTest(unittest.TestCase):

    def setUp(self):
        self.app = create_app("http://example.test:5000")
        self.client = self.app.test_client()

    def test_index_serves_the_app_shell(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Priotask", body)
        self.assertIn("http://example.test:5000", body)

    def test_index_includes_phase_8_task_organization_controls(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)
        for element_id in (
            "task-search", "task-type-filter", "task-subtype-filter", "task-sort",
            "show-done-checkbox", "new-task-type-select", "new-task-subtype-select",
        ):
            self.assertIn(element_id, body, f"{element_id} should be in the app shell")

    def test_static_js_modules_are_served(self):
        for filename in ("api.js", "session.js", "views.js", "app.js"):
            response = self.client.get(f"/static/js/{filename}")
            self.assertEqual(response.status_code, 200, f"{filename} should be served")


if __name__ == "__main__":
    unittest.main()
