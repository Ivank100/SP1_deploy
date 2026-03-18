# src/auth_utils.py
"""
Authentication utilities for JWT token generation/verification.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from ..core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    print(f"[DEBUG] Creating token with secret key length: {len(JWT_SECRET_KEY) if JWT_SECRET_KEY else 0}")
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        print(f"[DEBUG] JWT decode error: {type(e).__name__}: {e}")
        print(f"[DEBUG] Secret key: {JWT_SECRET_KEY[:10]}... (length: {len(JWT_SECRET_KEY)})")
        print(f"[DEBUG] Algorithm: {JWT_ALGORITHM}")
        print(f"[DEBUG] Token (first 50 chars): {token[:50]}...")
        return None
    except Exception as e:
        print(f"[DEBUG] Unexpected error decoding token: {type(e).__name__}: {e}")
        return None
