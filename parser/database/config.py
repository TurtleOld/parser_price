import os

from dotenv import load_dotenv
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import List

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

load_dotenv()


class Base(AsyncAttrs, DeclarativeBase):
    pass


metadata = MetaData()

engine = create_async_engine(
    os.environ.get("DATABASE_URL"),
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer())
    url: Mapped[str] = mapped_column(String(), unique=True)
    products: Mapped[List['Product']] = relationship(
        back_populates="messages",
        cascade="all, delete-orphan",
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"))
    available: Mapped[bool] = mapped_column(Boolean)
    url: Mapped[str] = mapped_column(String)
    product_name: Mapped[str] = mapped_column(String)
    store: Mapped[str] = mapped_column(String, nullable=True)
    picture: Mapped[str] = mapped_column(String)
    latest_price: Mapped[float] = mapped_column(Float)
    latest_price_ozon: Mapped[float] = mapped_column(Float)
    original_price: Mapped[float] = mapped_column(Float)
    messages: Mapped[List['Message']] = relationship(back_populates="products")
    prices_history: Mapped[List['PriceHistory']] = relationship(
        back_populates="products",
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"))
    updated_at = mapped_column(DateTime)
    price: Mapped[float] = mapped_column(Float)
    price_ozon: Mapped[float] = mapped_column(Float)
    original_price: Mapped[float] = mapped_column(Float)
    products: Mapped[List['Product']] = relationship(
        back_populates="prices_history",
    )
