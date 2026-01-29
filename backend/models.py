from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    dietary_profile = relationship("DietaryProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class DietaryProfile(Base):
    __tablename__ = "dietary_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Dietary restrictions
    halal = Column(Boolean, default=False)
    gluten_free = Column(Boolean, default=False)
    vegetarian = Column(Boolean, default=False)
    vegan = Column(Boolean, default=False)
    nut_free = Column(Boolean, default=False)
    dairy_free = Column(Boolean, default=False)
    
    # Allergens (stored as JSON array)
    allergens = Column(JSON, default=list)
    
    # Custom restrictions (stored as JSON array)
    custom_restrictions = Column(JSON, default=list)
    
    # LLM ingredient extractor preference
    use_llm_ingredient_extractor = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="dietary_profile")


class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Image and OCR data
    image_path = Column(String, nullable=True)
    barcode = Column(String, nullable=True)
    ocr_text = Column(Text, nullable=True)
    corrected_text = Column(Text, nullable=True)
    
    # Analysis results
    ingredients = Column(JSON, default=list)
    is_safe = Column(Boolean, nullable=True)
    warnings = Column(JSON, default=list)
    analysis_result = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="scans")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

