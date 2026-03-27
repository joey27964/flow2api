"""Authentication module"""

import bcrypt
import asyncio
from typing import Optional
from fastapi import Header, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import config
from .database import Database

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
db = Database()
_assigned_api_keys: set[str] = set()
_assigned_api_keys_lock = asyncio.Lock()


async def reload_assigned_api_keys() -> None:
    keys = await db.get_assigned_api_keys()
    async with _assigned_api_keys_lock:
        _assigned_api_keys.clear()
        for key in keys:
            normalized = key.strip()
            if normalized:
                _assigned_api_keys.add(normalized)


async def is_assigned_api_key(api_key: str) -> bool:
    if not api_key:
        return False
    async with _assigned_api_keys_lock:
        return api_key in _assigned_api_keys

class AuthManager:
    """Authentication manager"""

    @staticmethod
    def verify_api_key(api_key: str) -> bool:
        """Verify API key"""
        return api_key == config.api_key

    @staticmethod
    def verify_admin(username: str, password: str) -> bool:
        """Verify admin credentials"""
        # Compare with current config (which may be from database or config file)
        return username == config.admin_username and password == config.admin_password

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password"""
        return bcrypt.checkpw(password.encode(), hashed.encode())

async def verify_api_key_header(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify API key from Authorization header"""
    api_key = credentials.credentials
    if not AuthManager.verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


async def verify_api_key_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security),
    x_goog_api_key: Optional[str] = Header(None, alias="x-goog-api-key"),
    key: Optional[str] = Query(None),
) -> str:
    """Verify API key from Authorization header, x-goog-api-key header, or key query param."""
    api_key = None

    if credentials is not None:
        api_key = credentials.credentials
    elif x_goog_api_key:
        api_key = x_goog_api_key
    elif key:
        api_key = key

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Global key keeps existing behavior
    if AuthManager.verify_api_key(api_key):
        return api_key

    if not await is_assigned_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key
