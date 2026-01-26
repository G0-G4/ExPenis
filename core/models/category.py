from datetime import UTC, datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    type = Column(String, nullable=False)  # 'income' or 'expense'
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    transactions = relationship("UserTransaction", back_populates="category")
    
    def __repr__(self):
        return f"<Category(user_id={self.user_id}, type='{self.type}', name='{self.name}')>"
    
    def to_dict(self, recursive):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
