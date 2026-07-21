import sys
import os
import json
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.core.database import Base
from app.models.rag_document import RagDocument

def setup_database(engine):
    print("Thiết lập extension pgvector...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    
    print("Tạo bảng rag_documents nếu chưa tồn tại...")
    Base.metadata.create_all(bind=engine)

def embed_and_save():
    # 1. Khởi tạo Database
    engine = create_engine(settings.DATABASE_URL_SYNC)
    setup_database(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # 2. Đọc dữ liệu JSON
    file_path = r"d:\2026\duyen\DAS_Backend\data\sales_rag_data.json"
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file {file_path}")
        return
        
    print(f"Đang đọc dữ liệu từ {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    total_docs = len(data)
    print(f"Tìm thấy {total_docs} tài liệu cần nhúng từ file JSON.")
    
    # Kiểm tra xem dữ liệu đã có trong bảng chưa
    existing_count = session.query(RagDocument).count()
    if existing_count > 0:
        print(f"Hệ thống kiểm tra thấy đã có sẵn {existing_count} tài liệu RAG trong Database.")
        print("=> Bỏ qua bước Embedding để tránh mất thời gian. Nếu bạn muốn chạy lại, hãy xóa dữ liệu trong bảng rag_documents trước.")
        return
    
    # 3. Khởi tạo mô hình Embedding
    print("Đang tải mô hình sentence-transformers/all-MiniLM-L6-v2... (Sẽ mất thời gian nếu chạy lần đầu)")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Tải mô hình thành công!")
    
    # 4. Tiến hành Embedding và lưu DB (chạy theo batch)
    BATCH_SIZE = 100
    start_time = time.time()
    
    for i in range(0, total_docs, BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        
        # Trích xuất content để đưa vào model
        texts = [doc["content"] for doc in batch]
        
        # Nhúng (Embedding)
        embeddings = model.encode(texts, show_progress_bar=False)
        
        # Chuẩn bị object để lưu DB
        db_records = []
        for j, doc in enumerate(batch):
            db_records.append(
                RagDocument(
                    type=doc.get("type", "unknown"),
                    title=doc.get("title", ""),
                    content=doc["content"],
                    embedding=embeddings[j].tolist()  # Convert numpy array to list for SQLAlchemy pgvector
                )
            )
            
        # Bulk insert
        session.bulk_save_objects(db_records)
        session.commit()
        
        print(f"Đã xử lý {min(i + BATCH_SIZE, total_docs)} / {total_docs} tài liệu...")
        
    end_time = time.time()
    print(f"Hoàn tất quá trình nhúng dữ liệu vào PostgreSQL! Tổng thời gian: {end_time - start_time:.2f} giây.")

if __name__ == "__main__":
    embed_and_save()
