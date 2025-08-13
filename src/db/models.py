from sqlalchemy import Column, String, Integer, Text, JSON, BigInteger, TIMESTAMP, Boolean, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=True)
    public_alias = Column(String(80), nullable=True)  # alias shown instead of real name
    opt_in_public_analysis = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP, server_default='now()')

    # Relationship to media
    media = relationship("Media", back_populates="user")


class Media(Base):
    __tablename__ = 'media'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    media_type = Column(String(10))
    storage_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    keyframes = Column(JSON)
    size_bytes = Column(BigInteger)
    mime = Column(String(255))
    metadata = Column(JSON)
    created_at = Column(TIMESTAMP, server_default='now()')

    user = relationship("User", back_populates="media")


class Embedding(Base):
    __tablename__ = "embeddings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    vector = Column(ARRAY(Float), nullable=False)
    model = Column(String(255))
    created_at = Column(TIMESTAMP, server_default='now()')


class Face(Base):
    __tablename__ = "faces"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    bbox = Column(ARRAY(Float), nullable=False)  # [x,y,w,h]
    landmarks = Column(JSON)
    crop_url = Column(Text)
    created_at = Column(TIMESTAMP, server_default='now()')


class Detection(Base):
    __tablename__ = "detections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(255), nullable=False)
    score = Column(Float)
    bbox = Column(ARRAY(Float))  # [x,y,w,h]
    created_at = Column(TIMESTAMP, server_default='now()')
