# Script tạo tài khoản Admin mặc định
# Chạy: python -m app.seed
# Tạo user admin/admin123

import asyncio
from sqlalchemy import select

from app.core.database import async_session, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.sales_data import SalesData  # noqa: F401 - đảm bảo table được tạo


async def seed_admin():
    """Tạo tài khoản admin mặc định nếu chưa có"""

    # Tạo tất cả tables trước
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables đã được tạo/kiểm tra.")

    async with async_session() as session:
        # Kiểm tra admin đã tồn tại chưa
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("ℹ️  Tài khoản admin đã tồn tại. Bỏ qua.")
            return

        # Tạo admin mới
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
        print("✅ Đã tạo tài khoản admin thành công!")
        print(f"   👤 Username: admin")
        print(f"   🔑 Password: admin123")
        print(f"   🏷️  Role: ADMIN")
        print(f"   📧 Email: admin@das-system.vn")


async def main():
    print("=" * 50)
    print("🌱 DAS Backend - Seed Data")
    print("=" * 50)
    await seed_admin()
    print("=" * 50)
    print("✅ Seed hoàn tất!")


if __name__ == "__main__":
    asyncio.run(main())
