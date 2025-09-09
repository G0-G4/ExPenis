from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, UTC

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'income' or 'expense'
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    def __repr__(self):
        return f"<Transaction(user_id={self.user_id}, amount={self.amount}, category='{self.category}', type='{self.type}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'category': self.category,
            'type': self.type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }