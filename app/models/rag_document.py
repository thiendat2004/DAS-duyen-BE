import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class RagDocument(Base):
    __tablename__ = "rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, index=True)
    title = Column(String)
    content = Column(Text)
    
    # Sử dụng Vector với số chiều 384 (tương ứng model all-MiniLM-L6-v2)
    embedding = Column(Vector(384))
