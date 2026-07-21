from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from app.core.config import settings
from app.core.database import create_tables, close_db, async_session
from app.core.security import hash_password
from app.core.limiter import limiter

from app.models.user import User  # noqa: F401
from app.models.sales_data import SalesData  # noqa: F401

from app.api.v1.auth import router as auth_router
from app.api.v1.notifications import router as notifications_router


async def seed_admin_if_needed():
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        if result.scalar_one_or_none():
            return

        admin_user = User(
            username="admin",
            email="admin@das-system.vn",
            full_name="Administrator",
            hashed_password=hash_password("admin123"),
            role="ADMIN",
            status="ACTIVE",
        )
        session.add(admin_user)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await seed_admin_if_needed()
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API cho hệ thống DAS",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau."},
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path in ["/docs", "/redoc", "/openapi.json"]:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none';"
        )
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "frame-ancestors 'none';"
        )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.ngrok-free.dev", "frettiest-ariella-unnationally.ngrok-free.dev"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(notifications_router, prefix="/api/v1", tags=["Notifications"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "database": "postgresql",
        "version": settings.APP_VERSION,
    }
