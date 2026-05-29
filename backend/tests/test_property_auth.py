"""Property tests for Authentication features."""

import pytest
from hypothesis import given, settings, strategies as st
import jwt

from backend.services.auth_service import AuthService, SECRET_KEY, ALGORITHM
from backend.middleware.auth import get_current_user

class FakeUserRepo:
    def __init__(self):
        self.users = []
        
    async def find_by_username(self, username):
        for u in self.users:
            if u.get("username") == username:
                return u
        return None
        
    async def find_by_email(self, email):
        for u in self.users:
            if u.get("email") == email:
                return u
        return None
        
    async def create(self, data):
        import uuid
        data["user_id"] = str(uuid.uuid4())
        self.users.append(data)
        return data


# Feature: ipl-live-score-integration, Property 20: User Registration validation
@pytest.mark.asyncio
async def test_user_registration_validation():
    """
    **Validates: Requirements 5.2 (Auth integration)**
    """
    repo = FakeUserRepo()
    service = AuthService(repo)
    
    username = "testuser"
    email = "test@example.com"
    password = "SuperSecretPassword123!"
    
    # Register new user
    user = await service.register_user(username, email, password)
    assert user is not None
    assert user.username == username
    assert user.email == email
    assert user.password_hash != password # Should be hashed
    
    # Try register again with same username
    user2 = await service.register_user(username, "other@example.com", password)
    assert user2 is None
    
    # Try register again with same email
    user3 = await service.register_user("other_username", email, password)
    assert user3 is None


# Feature: ipl-live-score-integration, Property 23: Password Hashing verification
def test_password_hashing():
    """
    Property: Hashes are deterministic for verification but uniquely salted.
    """
    repo = FakeUserRepo()
    service = AuthService(repo)
    
    password = "SuperSecretPassword123!"
    hash1 = service.get_password_hash(password)
    hash2 = service.get_password_hash(password)
    
    # Salting means hashes should be different
    assert hash1 != hash2
    
    # But both should verify against the same password
    assert service.verify_password(password, hash1) is True
    assert service.verify_password(password, hash2) is True
    
    # Wrong password should fail
    assert service.verify_password("wrong_password", hash1) is False


# Feature: ipl-live-score-integration, Property 21: JWT Token Generation
@pytest.mark.asyncio
async def test_jwt_token_generation():
    repo = FakeUserRepo()
    service = AuthService(repo)
    
    user_id = "test_uuid"
    token = service.create_access_token({"sub": user_id, "username": "testuser"})
    
    # Verify token
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == user_id
    assert decoded["username"] == "testuser"
    assert "exp" in decoded


# Feature: ipl-live-score-integration, Property 24: Protected Endpoint Access Control
@pytest.mark.asyncio
async def test_protected_endpoint_access():
    # Valid token
    repo = FakeUserRepo()
    service = AuthService(repo)
    
    token = service.create_access_token({"sub": "test_uuid", "username": "testuser"})
    
    user = await get_current_user(token)
    assert user["user_id"] == "test_uuid"
    assert user["username"] == "testuser"
    
    # Missing token (Anonymous access allowed by get_current_user)
    anon_user = await get_current_user(None)
    assert anon_user["user_id"] is None
    assert anon_user["username"] == "Anonymous"
