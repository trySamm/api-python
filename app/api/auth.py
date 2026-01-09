"""Authentication API endpoints"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import Token, LoginRequest, RefreshRequest, UserCreate, UserResponse

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(user: User) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role.value,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user: User) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user is active"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control"""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker


async def verify_tenant_access(
    tenant_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Verify user has access to the specified tenant"""
    if current_user.role == UserRole.SUPER_ADMIN:
        return current_user
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )
    
    return current_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens"""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Generate tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    
    # Store refresh token
    user.refresh_token = refresh_token
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token"""
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if not user or user.refresh_token != request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Generate new tokens
    access_token = create_access_token(user)
    new_refresh_token = create_refresh_token(user)
    
    # Update refresh token (rotation)
    user.refresh_token = new_refresh_token
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout user by invalidating refresh token"""
    current_user.refresh_token = None
    await db.commit()
    return {"message": "Successfully logged out"}

