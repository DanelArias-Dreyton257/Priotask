import threading
import unittest

from server.src.data.db.DB import DB


class DBConcurrencyTest(unittest.TestCase):
    """Flask's dev server runs threaded by default, and every DAO shares one
    DB instance/connection - so DB.execute() has to be safe under concurrent
    calls from multiple threads. Before the fix, this reliably reproduced
    sqlite3.InterfaceError: "bad parameter or other API misuse" within a
    handful of iterations."""

    def test_concurrent_reads_and_writes_do_not_raise(self):
        db = DB(":memory:").connect()
        db.execute("INSERT INTO users (username, email) VALUES (?, ?)", ("alice", "a@example.com"))
        errors = []

        def hammer():
            try:
                for _ in range(200):
                    db.execute("SELECT * FROM users WHERE username = ?", ("alice",)).fetchone()
                    db.execute("SELECT * FROM users").fetchall()
                    db.execute(
                        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                        (f"tok-{threading.get_ident()}-{_}", 1, "2099-01-01T00:00:00"),
                    )
            except Exception as exc:  # noqa: BLE001 - the whole point is "did anything raise"
                errors.append(exc)

        threads = [threading.Thread(target=hammer) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])

    def test_execute_returns_last_row_id_for_insert(self):
        db = DB(":memory:").connect()
        result = db.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)", ("bob", "b@example.com"),
        )
        self.assertIsNotNone(result.lastrowid)

    def test_execute_fetchone_and_fetchall_after_insert(self):
        db = DB(":memory:").connect()
        db.execute("INSERT INTO users (username, email) VALUES (?, ?)", ("carol", "c@example.com"))
        self.assertEqual(db.execute("SELECT * FROM users").fetchone()["username"], "carol")
        self.assertEqual(len(db.execute("SELECT * FROM users").fetchall()), 1)

    def test_execute_fetchone_returns_none_for_no_match(self):
        db = DB(":memory:").connect()
        self.assertIsNone(db.execute("SELECT * FROM users WHERE username = ?", ("nobody",)).fetchone())


if __name__ == "__main__":
    unittest.main()
