"""Database models for voice system."""

from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, ForeignKey, LargeBinary, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Organization(Base):
    """Organization entity for multi-tenant support."""
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    users = relationship("User", back_populates="organization")
    voice_profiles = relationship("VoiceProfile", back_populates="organization")
    devices = relationship("Device", back_populates="organization")


class User(Base):
    """User entity."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    email = Column(String, nullable=False, unique=True)
    voice_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="users")
    voice_profiles = relationship("VoiceProfile", back_populates="user")
    devices = relationship("Device", back_populates="user")
    voice_sessions = relationship("VoiceSession", back_populates="user")


class VoiceProfile(Base):
    """Voice profile for speaker verification."""
    __tablename__ = "voice_profiles"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, default="Primary")
    
    # Encrypted embedding (serialized as JSON)
    embedding_encrypted = Column(LargeBinary, nullable=False)
    embedding_hash = Column(String, nullable=False)  # For verification
    
    confidence_threshold = Column(Float, default=0.85)
    anti_spoofing_enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active")  # active, inactive, training
    
    user = relationship("User", back_populates="voice_profiles")
    organization = relationship("Organization", back_populates="voice_profiles")


class Device(Base):
    """Device registered with voice automation."""
    __tablename__ = "devices"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String, nullable=False)
    device_type = Column(String)  # desktop, laptop, mobile
    device_id_hash = Column(String, nullable=False)  # Hardware ID hash
    os_type = Column(String)  # Windows, Linux, macOS
    
    voice_enabled = Column(Boolean, default=True)
    voice_profile_id = Column(String, ForeignKey("voice_profiles.id"))
    
    last_seen = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active")  # active, paused, revoked
    
    user = relationship("User", back_populates="devices")
    organization = relationship("Organization", back_populates="devices")
    voice_sessions = relationship("VoiceSession", back_populates="device")


class VoiceSession(Base):
    """Voice interaction session."""
    __tablename__ = "voice_sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"))
    device_id = Column(String, ForeignKey("devices.id"))
    
    wake_word = Column(String)
    speaker_id = Column(String)
    speaker_confidence = Column(Float)
    
    wake_word_detected_at = Column(DateTime)
    command_text = Column(String)
    command_confidence = Column(Float)
    
    execution_status = Column(String)  # success, failed, blocked, pending
    permission_required = Column(Boolean, default=False)
    permission_granted = Column(Boolean)
    
    is_genuine = Column(Boolean, default=True)  # Anti-spoofing result
    anti_spoofing_details = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="voice_sessions")
    device = relationship("Device", back_populates="voice_sessions")


class AutomationHistory(Base):
    """Record of automated actions executed via voice."""
    __tablename__ = "automation_history"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"))
    device_id = Column(String, ForeignKey("devices.id"))
    
    voice_session_id = Column(String, ForeignKey("voice_sessions.id"))
    
    command = Column(String, nullable=False)
    command_category = Column(String)  # application, file, system, etc.
    
    status = Column(String)  # success, failed, blocked
    error_message = Column(String)
    
    permission_level = Column(String)  # guest, user, trusted
    permission_required = Column(Boolean, default=False)
    required_confirmation = Column(Boolean, default=False)
    confirmation_provided = Column(Boolean)
    
    execution_time_ms = Column(Integer)
    
    executed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Audit trail
    ip_address = Column(String)
    user_agent = Column(String)
