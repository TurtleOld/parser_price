from sqlalchemy import create_engine, Column, String, Integer, UniqueConstraint, \
    ForeignKey, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)

    telegram_user_id = Column(String, unique=True)

    url = Column(String, unique=True)

    products = relationship("Product", back_populates="message",
                            cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)

    message_id = Column(Integer, ForeignKey('messages.id'))

    available = Column(
        String)

    url = Column(String)

    product_name = Column(String)

    picture = Column(String)
    latest_price = Column(Float)
    latest_price_ozon = Column(Float)
    original_price = Column(Float)
    message = relationship("Message", back_populates="products")
    prices_history = relationship("PriceHistory", back_populates="product",
                                  cascade="all, delete-orphan",)

class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    updated_at = Column(DateTime)
    price = Column(Float)
    price_ozon = Column(Float)
    original_price = Column(Float)
    product = relationship("Product", back_populates="prices_history")


engine = create_engine('sqlite:////app_data/telegram_user.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
