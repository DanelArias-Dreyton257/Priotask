class UserDTO:
    def __init__(self, username, password, email):
        self.username = username
        self.password = password
        self.email = email

    def __repr__(self):
        return f"UserDTO(username={self.username}, password={self.password}, email={self.email})"
