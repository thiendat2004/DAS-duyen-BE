from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.models.sales_data import SalesData
from app.core.config import settings

try:
    from google import genai
except ImportError:
    genai = None

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/chat")
async def chat_with_ai(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """API RAG đơn giản với Gemini AI"""
    if not settings.GEMINI_API_KEY or not genai:
        raise HTTPException(
            status_code=500, 
            detail="Tính năng AI chưa được cấu hình. Vui lòng cài đặt GEMINI_API_KEY trong .env và cài package google-genai."
        )

    # 1. Thu thập "Context" đơn giản từ Database (RAG)
    # Lấy tổng doanh thu
    rev_expr = func.sum(SalesData.price_unit * SalesData.units_sold)
    res_rev = await db.execute(select(rev_expr))
    total_rev = res_rev.scalar() or 0
    
    # Lấy top 3 danh mục
    res_cat = await db.execute(
        select(SalesData.category, rev_expr)\
        .group_by(SalesData.category)\
        .order_by(desc(rev_expr)).limit(3)
    )
    top_categories = ", ".join([f"{row[0]} ({row[1]:.0f} đ)" for row in res_cat.all()])

    # Lấy top 3 kênh bán
    res_chan = await db.execute(
        select(SalesData.channel, rev_expr)\
        .group_by(SalesData.channel)\
        .order_by(desc(rev_expr)).limit(3)
    )
    top_channels = ", ".join([f"{row[0]} ({row[1]:.0f} đ)" for row in res_chan.all()])

    # 2. Xây dựng Prompt
    context = f"""
    DỮ LIỆU TÓM TẮT HỆ THỐNG:
    - Tổng doanh thu toàn hệ thống: {total_rev:,.0f} đ
    - Top danh mục bán chạy: {top_categories}
    - Top kênh bán hàng: {top_channels}
    """

    prompt = f"""Bạn là trợ lý AI chuyên phân tích dữ liệu bán hàng của hệ thống quản lý FMCG (Data Analytics System - DAS).
    Dựa vào thông tin bối cảnh (context) lấy từ Database sau đây, hãy trả lời câu hỏi của người dùng. Nếu câu hỏi nằm ngoài ngữ cảnh dữ liệu, hãy trả lời theo kiến thức của bạn hoặc khuyên họ hỏi về số liệu.
    Luôn trả lời ngắn gọn, chuyên nghiệp, sử dụng tiếng Việt.
    
    {context}
    
    Câu hỏi của người dùng: {request.question}
    """

    # 3. Gọi Gemini API
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gọi AI: {str(e)}")
