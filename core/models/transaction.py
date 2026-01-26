from datetime import UTC, datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(user_id={self.user_id}, account_id={self.account_id}, amount={self.amount})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'category_id': self.category_id,
            'amount': self.amount,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
