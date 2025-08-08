from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    SIGNED_UP = "signed_up"
    NON_PI_ACCESS = "non_pi_access"  
    PI_ACCESS = "pi_access"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=True)  # Nullable for OAuth users
    role = Column(Enum(UserRole), default=UserRole.SIGNED_UP, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    user_logs = relationship("UserLog", back_populates="user", cascade="all, delete-orphan")
    chatbot_audits = relationship("ChatbotAudit", back_populates="user", cascade="all, delete-orphan")

    def has_pi_access(self) -> bool:
        """Check if user has PI (Personal Information) access"""
        return self.role == UserRole.PI_ACCESS

    def has_non_pi_access(self) -> bool:
        """Check if user has non-PI access"""
        return self.role in [UserRole.NON_PI_ACCESS, UserRole.PI_ACCESS]

    def can_access_document(self, is_pi_restricted: bool) -> bool:
        """Check if user can access a specific document based on PI restriction"""
        if is_pi_restricted:
            return self.has_pi_access()
        return self.has_non_pi_access() or self.role == UserRole.SIGNED_UP