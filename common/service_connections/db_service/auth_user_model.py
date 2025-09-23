from pydantic import BaseModel
from datetime import datetime, timezone



class AuthUserModel(BaseModel):
    """
    Schema for representing an authenticated user.
    """
     
    id: int | None = None
    email: str | None = None
    username: str | None = None
    current_token: str | None = None
    token_expires_at: datetime | None = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = datetime.now(tz=timezone.utc)
    last_login_at: datetime | None = None
    updated_at: datetime | None = None
