
class TokenManager:

    def __init__(self, token):
        self.token = token

    def get_token(self):
        return self.token

    def set_token(self, token):
        self.token = token

    def __repr__(self):
        return f"TokenManager(token={self.token})"
