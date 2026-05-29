"""Authentication middleware and dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError

try:
    from backend.services.auth_service import SECRET_KEY, ALGORITHM
except ModuleNotFoundError:
    from services.auth_service import SECRET_KEY, ALGORITHM


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to get the current authenticated user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        # Support anonymous users
        return {"user_id": None, "username": "Anonymous"}
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        if user_id is None:
            raise credentials_exception
            
        return {"user_id": user_id, "username": username}
    except InvalidTokenError:
        raise credentials_exception


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency for endpoints that require an authenticated user."""
    if current_user.get("user_id") is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user
