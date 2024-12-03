import os

from dotenv import load_dotenv
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

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
