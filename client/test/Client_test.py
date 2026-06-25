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

    def test_static_js_modules_are_served(self):
        for filename in ("api.js", "session.js", "views.js", "app.js"):
            response = self.client.get(f"/static/js/{filename}")
            self.assertEqual(response.status_code, 200, f"{filename} should be served")


if __name__ == "__main__":
    unittest.main()
