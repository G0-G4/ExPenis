import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./expenis.db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session factory
session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session_async():
    """Get database session"""
    async with session_maker() as session:
        yield session

def get_session():
    """Get database session (synchronous context)"""
    return session_maker()
