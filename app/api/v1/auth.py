from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
    verify_token,
    get_current_user,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, TokenRefreshResponse, UserBrief, UserResponse

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.username == login_data.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng.",
        )

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        remaining_lock = int((user.locked_until - now).total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tài khoản đang bị khóa. Vui lòng thử lại sau {remaining_lock} phút.",
        )

    if not verify_password(login_data.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng.",
        )

    if user.status and user.status.upper() != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa hoặc vô hiệu hóa.",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    user_id_str = str(user.id)
    access_token = create_access_token(data={"sub": user_id_str})
    refresh_token = create_refresh_token(data={"sub": user_id_str})

    user.hashed_refresh_token = hash_token(refresh_token)
    user.refresh_token_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )

    return TokenResponse(
        accessToken=access_token,
        user=UserBrief(
            id=user_id_str,
            username=user.username,
            email=user.email,
            role=user.role,
        ),
    )


@router.post("/auth/refresh", response_model=TokenRefreshResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )

    try:
        payload = decode_refresh_token(refresh_token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy thông tin phiên đăng nhập.",
        )

    now = datetime.now(timezone.utc)
    if user.refresh_token_expires_at and user.refresh_token_expires_at < now:
        user.hashed_refresh_token = None
        user.refresh_token_expires_at = None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
        )

    if not verify_token(refresh_token, user.hashed_refresh_token):
        user.hashed_refresh_token = None
        user.refresh_token_expires_at = None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cảnh báo bảo mật: Token không hợp lệ. Vui lòng đăng nhập lại.",
        )

    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    user.hashed_refresh_token = hash_token(new_refresh_token)
    user.refresh_token_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )

    return TokenRefreshResponse(
        accessToken=new_access_token,
        user=UserBrief(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
        ),
    )


@router.post("/auth/logout")
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id: str = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.hashed_refresh_token = None
                    user.refresh_token_expires_at = None
                    await db.commit()
        except Exception:
            pass

    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Đăng xuất thành công."}


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        role=current_user.role,
        status=current_user.status,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
    )
