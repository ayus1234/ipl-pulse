"""Service for user authentication and session management."""

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

try:
    from backend.database.models import User
    from backend.database.repository import UserRepository
except ModuleNotFoundError:
    from database.models import User
    from database.repository import UserRepository

# Secret key for JWT (In production, this should be an environment variable)
SECRET_KEY = "ipl_pulse_super_secret_jwt_key_for_demo_only"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

class AuthService:
    """Handles user registration, login, and JWT generation."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        try:
            return bcrypt.checkpw(
                plain_password[:72].encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except ValueError:
            return False

    def get_password_hash(self, password: str) -> str:
        """Generate a hash from a password."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password[:72].encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def register_user(self, username: str, email: str, password: str) -> Optional[User]:
        """Register a new user."""
        # Check if username or email already exists
        existing_user = await self.user_repo.find_by_username(username)
        if existing_user:
            return None # Username taken
            
        existing_email = await self.user_repo.find_by_email(email)
        if existing_email:
            return None # Email taken

        hashed_password = self.get_password_hash(password)
        
        user_data = User(username=username, email=email, password_hash=hashed_password)
        saved = await self.user_repo.create(user_data.model_dump(mode="json"))
        return User.model_validate(saved)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        user_dict = await self.user_repo.find_by_username(username)
        if not user_dict:
            return None
            
        user = User.model_validate(user_dict)
        if not user.password_hash or not self.verify_password(password, user.password_hash):
            return None
            
        return user
