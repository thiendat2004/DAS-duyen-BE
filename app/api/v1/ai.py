import asyncio
import json
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sentence_transformers import SentenceTransformer

from app.core.database import get_db
from app.models.rag_document import RagDocument
from app.core.config import settings

import google.generativeai as genai

router = APIRouter()

# Warm load embedding model into memory on startup
print("Đang khởi tạo model embedding sentence-transformers...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")


class ChatRequest(BaseModel):
    question: str
    provider: Optional[str] = None  # Lựa chọn tùy chỉnh từ FE: "auto", "gemini", "llama"

async def generate_ollama_stream(prompt: str):
    """Hàm stream từ mô hình Llama3.2 chạy Local via Ollama"""
    print("🤖 Đang sử dụng mô hình Local Llama 3.2 (llama3.2:3b)...")
    url = "http://localhost:11434/api/generate"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json={"model": "llama3.2:3b", "prompt": prompt}) as response:
                if response.status_code != 200:
                    yield f"*(Lỗi Ollama Status {response.status_code}: Không thể chạy model llama3.2:3b)*"
                    return
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk
                                await asyncio.sleep(0.01)
                        except Exception:
                            continue
    except Exception as e:
        print(f"Lỗi khi gọi Ollama Local: {e}")
        yield f"\n\n*(Không thể kết nối với mô hình Llama 3.2 Local: {str(e)})*"

@router.post("/chat")
async def chat_with_ai(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """API RAG + GenAI chọn lựa Provider (Gemini / Llama 3.2 / Auto)"""
    
    # Xác định provider muốn dùng (Ưu tiên từ Request body -> rồi tới file .env)
    chosen_provider = (request.provider or getattr(settings, "AI_PROVIDER", "auto")).lower()
    
    # 1. Mã hóa câu hỏi thành Vector không làm nghẽn Async Event Loop
    question_embedding = await asyncio.to_thread(
        lambda: embed_model.encode([request.question])[0].tolist()
    )
    
    # 2. Truy vấn RAG từ PostgreSQL (Tìm 8 tài liệu gần nhất)
    res = await db.execute(
        select(RagDocument)
        .order_by(RagDocument.embedding.cosine_distance(question_embedding))
        .limit(10)
    )
    docs = res.scalars().all()
    
    # Tạo chuỗi bối cảnh đầy đủ
    context_parts = []
    for i, d in enumerate(docs):
        context_parts.append(f"Tài liệu {i+1} [{d.type}]: {d.title} - {d.content}")
        
    context_text = "\n\n".join(context_parts)
    
    # 3. Xây dựng Prompt chuẩn hóa
    prompt = f"""Bạn là chuyên gia phân tích dữ liệu bán hàng FMCG của hệ thống DAS.

Ngữ cảnh:
- Hệ thống lưu trữ dữ liệu về doanh số, số lượng bán, tồn kho, SKU, thương hiệu, danh mục sản phẩm, khu vực, kênh bán hàng và thời gian.
- Dữ liệu được lấy từ hệ thống RAG và luôn được xem là nguồn thông tin duy nhất.

Yêu cầu:
1. Trả lời chính xác, đầy đủ và trực tiếp vào câu hỏi dựa trên DỮ LIỆU BỐI CẢNH.
2. Không tự tạo thêm số liệu không có trong dữ liệu.
3. Chỉ khi hoàn toàn KHÔNG có thông tin trong Bối cảnh để trả lời, mới đáp: "Không tìm thấy dữ liệu phù hợp trong hệ thống."
4. Trả lời bằng tiếng Việt.

Định dạng:
- Dùng tiêu đề ngắn nếu cần.
- In đậm các giá trị quan trọng.
- Sử dụng danh sách gạch đầu dòng.

=== DỮ LIỆU BỐI CẢNH (RAG CONTEXT) ===
{context_text}
=======================================

Câu hỏi: {request.question}
"""

    # 4. Xử lý theo Provider được chỉ định
    if chosen_provider == "llama":
        # Ép dùng Llama 3.2 Local
        return StreamingResponse(generate_ollama_stream(prompt), media_type="text/plain")
        
    elif chosen_provider == "gemini":
        # Ép dùng Cloud Gemini
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=400, detail="Chưa cấu hình GEMINI_API_KEY trong file .env")
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-3.5-flash')
            gemini_response = await asyncio.to_thread(
                lambda: model.generate_content(prompt, stream=True)
            )
            
            async def async_gemini_generator():
                try:
                    for chunk in gemini_response:
                        text_content = ""
                        try:
                            text_content = chunk.text
                        except Exception:
                            if hasattr(chunk, 'candidates') and chunk.candidates:
                                c = chunk.candidates[0]
                                if c.content and c.content.parts:
                                    text_content = "".join([p.text for p in c.content.parts if hasattr(p, 'text')])
                        if text_content:
                            yield text_content
                            await asyncio.sleep(0.01)
                except Exception as stream_err:
                    yield f"\n\n*(Lỗi gián đoạn stream: {str(stream_err)})*"
                        
            return StreamingResponse(async_gemini_generator(), media_type="text/plain")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi Cloud Gemini: {str(e)}")

    else:
        # Chế độ "auto": Thử Gemini trước, nếu bị lỗi/429 sẽ tự chuyển sang Llama 3.2 Local
        use_local = False
        gemini_response = None
        
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                models_to_try = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.5-flash','gemini-3.5-flash']
                for model_name in models_to_try:
                    try:
                        m = genai.GenerativeModel(model_name)
                        current_model = m
                        gemini_response = await asyncio.to_thread(
                            lambda: current_model.generate_content(prompt, stream=True)
                        )
                        print(f"⚡ Đã kết nối thành công với Cloud Gemini ({model_name})")
                        break
                    except Exception as e:
                        err_str = str(e)
                        if "429" in err_str or "Quota" in err_str or "rate-limits" in err_str or "404" in err_str:
                            print(f"Model {model_name} bị hạn chế Quota hoặc lỗi, thử model tiếp theo...")
                            continue
                        else:
                            raise e
                            
                if gemini_response is None:
                    print("⚠️ Tất cả các model Cloud Gemini đều bị hết Quota. Chuyển sang mô hình Local Llama 3.2...")
                    use_local = True
            except Exception as e:
                print(f"⚠️ Lỗi Cloud Gemini: {e}. Chuyển sang mô hình Local Llama 3.2...")
                use_local = True
        else:
            use_local = True

        if use_local:
            return StreamingResponse(generate_ollama_stream(prompt), media_type="text/plain")
        else:
            async def async_gemini_generator():
                try:
                    for chunk in gemini_response:
                        text_content = ""
                        try:
                            text_content = chunk.text
                        except Exception:
                            if hasattr(chunk, 'candidates') and chunk.candidates:
                                c = chunk.candidates[0]
                                if c.content and c.content.parts:
                                    text_content = "".join([p.text for p in c.content.parts if hasattr(p, 'text')])
                        if text_content:
                            yield text_content
                            await asyncio.sleep(0.01)
                except Exception as stream_err:
                    yield f"\n\n*(Lỗi gián đoạn stream: {str(stream_err)})*"
                        
            return StreamingResponse(async_gemini_generator(), media_type="text/plain")
