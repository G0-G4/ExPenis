from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, UTC
from sqlalchemy.sql import func

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Account(user_id={self.user_id}, name='{self.name}', amount={self.amount})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'amount': self.amount,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
