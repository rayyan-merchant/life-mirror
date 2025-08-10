from sqlalchemy import Column, String, Integer, Text, JSON, BigInteger, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Media(Base):
    __tablename__ = 'media'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    media_type = Column(String(10))
    storage_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    keyframes = Column(JSON)
    size_bytes = Column(BigInteger)
    mime = Column(String(255))
    metadata = Column(JSON)
    created_at = Column(TIMESTAMP, server_default='now()')
