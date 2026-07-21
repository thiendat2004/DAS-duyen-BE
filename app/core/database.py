from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG, 
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# model 
class Base(DeclarativeBase):
    pass



async def get_db():
    """Tạo database session cho mỗi request, tự đóng khi xong"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Tạo tất cả bảng dựa trên models đã định nghĩa"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Đóng kết nối database
async def close_db():
    """Đóng database engine khi ứng dụng shutdown"""
    await engine.dispose()
