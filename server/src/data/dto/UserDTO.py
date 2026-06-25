from dataclasses import dataclass
from typing import Optional


@dataclass
class UserDTO:
    """Wire-format view of a User. Never carries the password hash/salt."""
    user_id: Optional[int]
    username: str
    email: str
