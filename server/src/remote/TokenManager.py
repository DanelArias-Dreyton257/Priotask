'''
This class is used to manage the token for the remote server.
It is a singleton class, so only one instance of it can exist
at a time.
'''


class TokenManager:

    def __init__(self, token):
        self.token = token

    def get_token(self):
        return self.token

    def set_token(self, token):
        self.token = token

    def __repr__(self):
        return f"TokenManager(token={self.token})"
