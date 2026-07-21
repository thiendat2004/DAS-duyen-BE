import sys
import os
import csv
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Thêm thư mục gốc vào sys.path để import từ app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.sales_data import SalesData
from app.core.database import Base

def import_csv():
    # Sử dụng DATABASE_URL_SYNC để dùng engine đồng bộ cho tác vụ import
    engine = create_engine(settings.DATABASE_URL_SYNC)
    
    # Tạo bảng nếu chưa tồn tại
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    csv_file_path = r"D:\2026\duyen\FMCG_data_clean_final.csv"
    
    if not os.path.exists(csv_file_path):
        print(f"Không tìm thấy file: {csv_file_path}")
        return

    print("Đang xóa dữ liệu cũ (nếu có)...")
    session.query(SalesData).delete()
    session.commit()

    print("Đang đọc và import dữ liệu từ CSV...")
    records_to_insert = []
    
    with open(csv_file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse date DD/MM/YYYY
            try:
                date_obj = datetime.strptime(row["date"], "%d/%m/%Y").date()
            except ValueError:
                date_obj = datetime.strptime(row["date"], "%Y-%m-%d").date() # Fallback

            # Chuyển đổi các giá trị kiểu số
            price_unit = float(row.get("price_unit", 0) or 0)
            promotion_flag = int(float(row.get("promotion_flag", 0) or 0))
            delivery_days = int(float(row.get("delivery_days", 0) or 0))
            stock_available = int(float(row.get("stock_available", 0) or 0))
            delivered_qty = int(float(row.get("delivered_qty", 0) or 0))
            units_sold = int(float(row.get("units_sold", 0) or 0))

            sale_data = SalesData(
                date=date_obj,
                sku=row.get("sku", ""),
                brand=row.get("brand", ""),
                segment=row.get("segment", ""),
                category=row.get("category", ""),
                channel=row.get("channel", ""),
                region=row.get("region", ""),
                pack_type=row.get("pack_type", ""),
                price_unit=price_unit,
                promotion_flag=promotion_flag,
                delivery_days=delivery_days,
                stock_available=stock_available,
                delivered_qty=delivered_qty,
                units_sold=units_sold,
            )
            records_to_insert.append(sale_data)

    if records_to_insert:
        # Tối ưu hóa: thêm bulk để nhanh hơn
        session.bulk_save_objects(records_to_insert)
        session.commit()
        print(f"✅ Import thành công {len(records_to_insert)} records.")
    else:
        print("⚠️ File CSV không có dữ liệu.")
        
    session.close()

if __name__ == "__main__":
    import_csv()
