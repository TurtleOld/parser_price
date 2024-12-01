import os

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
)
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship

load_dotenv()


class Base(AsyncAttrs, DeclarativeBase):
    pass


metadata = MetaData()


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer)
    url = Column(String, unique=True)
    products = relationship(
        "Product", back_populates="message", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    available = Column(Boolean)
    url = Column(String)
    product_name = Column(String)
    store = Column(String, nullable=True)
    picture = Column(String)
    latest_price = Column(Float)
    latest_price_ozon = Column(Float)
    original_price = Column(Float)
    message = relationship("Message", back_populates="products")
    prices_history = relationship(
        "PriceHistory",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    updated_at = Column(DateTime)
    price = Column(Float)
    price_ozon = Column(Float)
    original_price = Column(Float)
    product = relationship("Product", back_populates="prices_history")


engine = create_async_engine(
    os.environ.get("DATABASE_URL"),
    pool_size=20,
    max_overflow=10,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
