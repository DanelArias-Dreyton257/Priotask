from server.data.db.DB import DB


class TaskDAO (object):
    def __init__(self):
        self.db = DB()
        self.db.connect()

    def get_task(self, task_id):
        query = "SELECT * FROM tasks WHERE task_id = ?"
        self.db.execute(query, (task_id,))
        return self.db.fetchone()

    def get_tasks(self):
        query = "SELECT * FROM tasks"
        self.db.execute(query)
        return self.db.fetchall()

    def add_task(self, name, deadline, expected_duration, importance):
        query = "INSERT INTO tasks (name, deadline, expected_duration, importance) VALUES (?,?,?,?)"
        self.db.execute(query, (name, deadline, expected_duration, importance))
