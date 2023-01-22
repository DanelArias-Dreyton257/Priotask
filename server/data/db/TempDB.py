from server.data.domain import User, Task


'''
This class is used to replace the actual database. It is used to test the server.
Implements the same methods as the actual database but does not connect to a database.
It would implement a mock database that would store data in a text file. The values are separated by a semicolon like a csv file.
First the users are stored and then the tasks. The structure is as follows:
Number_of_users
user;username;password;email
user;username;password;email
...
Number_of_tasks
task;task_id;name;deadline;expected_duration;importance
task;task_id;name;deadline;expected_duration;importance
...

'''


class TempDB:
    def __init__(self):
        self.users = []
        self.tasks = []
        self.selected = {"from_index": 0, "to_index": -1, "list_name": "users"}

        self.file_path = "server/data/db/temp/temp_db.txt"

    def connect(self):
        # Read from the file
        with open(self.file_path, "r") as file:
            for line in file:
                if line == "":
                    break
                else:
                    line = line.split(";")
                    if line[0] == "user":
                        self.users.append(User(line[1], line[2], line[3]))
                    elif line[0] == "task":
                        self.tasks.append(
                            Task(line[1], line[2], line[3], line[4]))

    def execute(self, query, params=None):

        def ex_select(query, params):
            # SELECT * FROM table
            if query[1] == "*":
                if query[3] == "users":
                    self.selected["from_index"] = 0
                    self.selected["to_index"] = len(self.users)
                    self.selected["list_name"] = "users"
                elif query[3] == "tasks":
                    self.selected["from_index"] = 0
                    self.selected["to_index"] = len(self.tasks)
                    self.selected["list_name"] = "tasks"
            # SELECT * FROM users WHERE username = "username"
            elif query[1] == "username" and query[3] == "users" and query[4] == "WHERE":
                for i in range(len(self.users)):
                    if self.users[i].username == params[0]:
                        self.selected["from_index"] = i
                        self.selected["to_index"] = i + 1
                        self.selected["list_name"] = "users"
                        break
            # SELECT * FROM tasks WHERE task_id = "task_id"
            elif query[1] == "task_id" and query[3] == "tasks" and query[4] == "WHERE":
                for i in range(len(self.tasks)):
                    if self.tasks[i].task_id == params[0]:
                        self.selected["from_index"] = i
                        self.selected["to_index"] = i + 1
                        self.selected["list_name"] = "tasks"
                        break

        def ex_insert(query, params):
            # INSERT INTO users (username, password, email) VALUES (?,?,?)
            if query[2] == "users":
                self.users.append(User(params[0], params[1], params[2]))
            # INSERT INTO tasks (name, deadline, expected_duration, importance) VALUES (?,?,?,?)
            elif query[2] == "tasks":
                self.tasks.append(
                    Task(params[0], params[1], params[2], params[3]))

        def ex_delete(query, params):
            # DELETE FROM users WHERE username = "username"
            if query[2] == "users" and query[3] == "WHERE":
                for i in range(len(self.users)):
                    if self.users[i].username == params[0]:
                        self.users.pop(i)
                        break
            # DELETE FROM tasks WHERE task_id = "task_id"
            elif query[2] == "tasks" and query[3] == "WHERE":
                for i in range(len(self.tasks)):
                    if self.tasks[i].task_id == params[0]:
                        self.tasks.pop(i)
                        break

        def ex_update(query, params):
            # UPDATE users SET password = "password" WHERE username = "username"
            if query[1] == "users" and query[2] == "SET" and query[4] == "WHERE":
                for i in range(len(self.users)):
                    if self.users[i].username == params[1]:
                        self.users[i].password = params[0]
                        break
            # UPDATE tasks SET name = "name", deadline = "deadline", expected_duration = "expected_duration", importance = "importance" WHERE task_id = "task_id"
            elif query[1] == "tasks" and query[2] == "SET" and query[6] == "WHERE":
                for i in range(len(self.tasks)):
                    if self.tasks[i].task_id == params[4]:
                        self.tasks[i].name = params[0]
                        self.tasks[i].deadline = params[1]
                        self.tasks[i].expected_duration = params[2]
                        self.tasks[i].importance = params[3]
                        break

        # Read the query (the important part is the first word)
        query = query.split(" ")
        # Make a switch case
        if query[0] == "SELECT":
            ex_select(query, params)
        elif query[0] == "INSERT":
            ex_insert(query, params)
        elif query[0] == "DELETE":
            ex_delete(query, params)
        elif query[0] == "UPDATE":
            ex_update(query, params)

    def fetchone(self):
        # Take the first element from the selected list
        if self.selected["from_index"] < self.selected["to_index"]:
            if self.selected["list_name"] == "users":
                return self.users[self.selected["from_index"]]
            elif self.selected["list_name"] == "tasks":
                return self.tasks[self.selected["from_index"]]

            # Increment the index
            self.selected["from_index"] += 1

    def fetchall(self):
        # Take all the elements from the selected list
        if self.selected["from_index"] < self.selected["to_index"]:
            if self.selected["list_name"] == "users":
                return self.users[self.selected["from_index"]:self.selected["to_index"]]
            elif self.selected["list_name"] == "tasks":
                return self.tasks[self.selected["from_index"]:self.selected["to_index"]]

            # Increment the index
            self.selected["from_index"] = self.selected["to_index"]

    def close(self):
        # Write in the file
        with open(self.file_path, "w") as file:
            file.write(str(len(self.users)) + "\n")
            for user in self.users:
                file.write("user;" + user.username + ";" +
                           user.password + ";" + user.email + "\n")
            file.write(str(len(self.tasks)) + "\n")
            for i in range(len(self.tasks)):
                task_id = i + 1
                file.write("task;" + str(task_id) + ";" + self.tasks[i].name + ";" + self.tasks[i].deadline +
                           ";" + self.tasks[i].expected_duration + ";" + self.tasks[i].importance + "\n")
