# Model SalesData - Dữ liệu bán hàng từ Power BI CSV
# Bảng chính chứa tất cả dữ liệu phân tích

import uuid
from datetime import datetime, date, timezone

from sqlalchemy import Column, String, DateTime, Date, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class SalesData(Base):
    """
    Bảng sales_data - Lưu dữ liệu bán hàng từ CSV/Power BI
    Các cột tương ứng với file CSV đã lọc từ Power BI:
    Date, sku, brand, segment, category, channel, region,
    pack_type, price_unit, promotion_flag, delivery_days,
    stock_available, delivered_qty, units_sold
    """

    __tablename__ = "sales_data"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Ngày giao dịch
    date = Column(Date, nullable=False, index=True)

    # Thông tin sản phẩm
    sku = Column(String(50), nullable=False, index=True)
    brand = Column(String(100), nullable=True)
    segment = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True, index=True)

    # Kênh bán và khu vực
    channel = Column(String(50), nullable=True, index=True)    # Discount, E-commerce, Retail
    region = Column(String(50), nullable=True, index=True)     # Pl-Central, Pl-North, Pl-South

    # Đóng gói
    pack_type = Column(String(50), nullable=True)              # Single, Multipack, Carton

    # Giá và khuyến mãi
    price_unit = Column(Float, nullable=True, default=0)       # Giá đơn vị
    promotion_flag = Column(Integer, nullable=True, default=0) # Cờ khuyến mãi (0/1)

    # Giao hàng
    delivery_days = Column(Integer, nullable=True, default=0)  # Số ngày giao hàng

    # Kho hàng
    stock_available = Column(Integer, nullable=True, default=0)  # Tồn kho hiện có

    # Số lượng
    delivered_qty = Column(Integer, nullable=True, default=0)  # Số lượng đã giao
    units_sold = Column(Integer, nullable=True, default=0)     # Số lượng đã bán

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<SalesData(date={self.date}, sku={self.sku}, channel={self.channel})>"
