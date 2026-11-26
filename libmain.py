from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker,mapped_column, Mapped,DeclarativeBase,relationship, Session
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional
import os 
load_dotenv()
url = os.getenv("DATABASE_URL")

class Base(DeclarativeBase):
    pass

class Author(Base):
    __tablename__ = "author"
    id:Mapped[int] = mapped_column(primary_key= True) 
    name:Mapped[str]
    books: Mapped[list["Book"]] = relationship(back_populates="author")

class Book(Base):
    __tablename__ = "book"
    id:Mapped[int] = mapped_column(primary_key=True) 
    title: Mapped[str] = mapped_column()
    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))
    author:Mapped[Author] = relationship(back_populates="books")

class User(Base):
    __tablename__ = "users"
    id:Mapped[int] = mapped_column(primary_key=True)
    name:Mapped[str] = mapped_column()
    email:Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column()

class Loan(Base):
    __tablename__ = "loans"
    id:Mapped[int] = mapped_column(primary_key=True)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id"))
    book_id: Mapped[int] = mapped_column(ForeignKey("book.id"))
    borrowed_at: Mapped[datetime] = mapped_column(default=datetime.now)
    due_at:Mapped[datetime] = mapped_column(default=(datetime.now() + timedelta(days=14)))
    returned_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    late_fee: Mapped[int] = mapped_column(default=0)
    
engine = create_engine(url) #url

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
print(Base.metadata.tables.keys())
def get_session():
    session = SessionLocal()
    try:
        yield session    
        
    finally:
        session.close()

