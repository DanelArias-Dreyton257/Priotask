from server.data.db.DB import DB


class UserDAO (object):
    def __init__(self):
        self.db = DB()
        self.db.connect()

    def get_user(self, username):
        query = "SELECT * FROM users WHERE username = ?"
        self.db.execute(query, (username,))
        return self.db.fetchone()

    def get_users(self):
        query = "SELECT * FROM users"
        self.db.execute(query)
        return self.db.fetchall()

    def add_user(self, username, password, email):
        query = "INSERT INTO users (username, password, email) VALUES (?,?,?)"
        self.db.execute(query, (username, password, email))
