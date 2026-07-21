from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.models.sales_data import SalesData

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_data(db: AsyncSession = Depends(get_db)):
    """API cho trang Tổng quan"""
    # Tính tổng doanh thu: sum(price_unit * units_sold)
    revenue_expr = func.sum(SalesData.price_unit * SalesData.units_sold)
    
    # 1. Tổng doanh thu
    res = await db.execute(select(revenue_expr))
    total_revenue = res.scalar() or 0
    
    # 2. Tổng số sản phẩm (SKU)
    res_sku = await db.execute(select(func.count(func.distinct(SalesData.sku))))
    total_products = res_sku.scalar() or 0
    
    # 3. Đơn hàng/số lượng đã bán
    res_sold = await db.execute(select(func.sum(SalesData.units_sold)))
    units_sold = res_sold.scalar() or 0
    
    # 4. Kênh đang hoạt động
    res_channel = await db.execute(select(func.count(func.distinct(SalesData.channel))))
    total_channels = res_channel.scalar() or 0

    return {
        "total_revenue": total_revenue,
        "total_products": total_products,
        "units_sold": units_sold,
        "total_channels": total_channels
    }

@router.get("/revenue")
async def get_revenue_data(db: AsyncSession = Depends(get_db)):
    """API cho trang Doanh thu (Theo category)"""
    revenue_expr = func.sum(SalesData.price_unit * SalesData.units_sold)
    
    query = select(SalesData.category, revenue_expr.label("revenue"))\
        .group_by(SalesData.category)\
        .order_by(desc("revenue"))
        
    result = await db.execute(query)
    data = [{"category": row[0], "revenue": row[1]} for row in result.all()]
    
    return {"by_category": data}

@router.get("/products")
async def get_products_data(db: AsyncSession = Depends(get_db)):
    """API cho trang Sản phẩm (Top bán chạy)"""
    revenue_expr = func.sum(SalesData.price_unit * SalesData.units_sold)
    units_expr = func.sum(SalesData.units_sold)
    
    query = select(SalesData.sku, SalesData.brand, units_expr.label("units"), revenue_expr.label("revenue"))\
        .group_by(SalesData.sku, SalesData.brand)\
        .order_by(desc("units"))\
        .limit(10)
        
    result = await db.execute(query)
    data = [{"sku": row[0], "brand": row[1], "units_sold": row[2], "revenue": row[3]} for row in result.all()]
    
    return {"top_products": data}

@router.get("/sales")
async def get_sales_data(db: AsyncSession = Depends(get_db)):
    """API cho trang Đơn hàng (Khuyến mãi, Đóng gói)"""
    units_expr = func.sum(SalesData.units_sold)
    
    # Theo pack_type
    query_pack = select(SalesData.pack_type, units_expr.label("units"))\
        .group_by(SalesData.pack_type)
    res_pack = await db.execute(query_pack)
    by_pack = [{"pack_type": row[0], "units_sold": row[1]} for row in res_pack.all()]
    
    # Theo khuyến mãi
    query_promo = select(SalesData.promotion_flag, units_expr.label("units"))\
        .group_by(SalesData.promotion_flag)
    res_promo = await db.execute(query_promo)
    by_promo = [{"promotion": bool(row[0]), "units_sold": row[1]} for row in res_promo.all()]
    
    return {"by_pack_type": by_pack, "by_promotion": by_promo}

@router.get("/warehouse")
async def get_warehouse_data(db: AsyncSession = Depends(get_db)):
    """API cho trang Kho hàng"""
    stock_expr = func.sum(SalesData.stock_available)
    delivery_expr = func.avg(SalesData.delivery_days)
    
    query = select(SalesData.category, stock_expr.label("stock"), delivery_expr.label("avg_delivery"))\
        .group_by(SalesData.category)
        
    res = await db.execute(query)
    data = [{"category": row[0], "stock_available": row[1], "avg_delivery_days": float(row[2])} for row in res.all()]
    
    return {"warehouse_status": data}

@router.get("/sites")
async def get_sites_data(db: AsyncSession = Depends(get_db)):
    """API cho trang Kênh & Khu vực"""
    revenue_expr = func.sum(SalesData.price_unit * SalesData.units_sold)
    units_expr = func.sum(SalesData.units_sold)
    
    # By Channel
    q_channel = select(SalesData.channel, revenue_expr, units_expr)\
        .group_by(SalesData.channel)
    res_channel = await db.execute(q_channel)
    by_channel = [{"channel": row[0], "revenue": row[1], "units_sold": row[2]} for row in res_channel.all()]
    
    # By Region
    q_region = select(SalesData.region, revenue_expr)\
        .group_by(SalesData.region)
    res_region = await db.execute(q_region)
    by_region = [{"region": row[0], "revenue": row[1]} for row in res_region.all()]
    return {"by_channel": by_channel, "by_region": by_region}

@router.get("/report")
async def get_report_data(db: AsyncSession = Depends(get_db), limit: int = 50):
    """API cho trang Báo cáo (Dữ liệu thô)"""
    query = select(SalesData).order_by(desc(SalesData.date)).limit(limit)
    res = await db.execute(query)
    
    data = []
    for row in res.scalars():
        data.append({
            "date": row.date.isoformat(),
            "sku": row.sku,
            "category": row.category,
            "channel": row.channel,
            "units_sold": row.units_sold,
            "revenue": row.price_unit * row.units_sold
        })
    return {"data": data}
