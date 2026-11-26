from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel,ConfigDict
from libmain import get_session,Author,Book,Session,sessionmaker, User,Loan
from datetime import datetime
from typing import Optional
from sqlalchemy.exc import IntegrityError #for email repeating error!
from sqlalchemy import select , Column, Integer, DateTime
from jose import JWTError
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from libken import create_token,read_token

class LogIn(BaseModel):
    email:str
    password:str

class AuthorIn(BaseModel):
    name: str

class AuthorOut(BaseModel):
    id: int
    name:str
    model_config = ConfigDict(from_attributes=True) #need to understand 
class AuthorShort(BaseModel):
    name:str
    model_config = ConfigDict(from_attributes=True)

class BookIn(BaseModel):
    title: str

class BookCreate(BaseModel):
    author_id: int
    title: str


class BookOut(BaseModel):
    id: int
    title: str
    author_id: int
    author: AuthorShort
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
class UserOut(BaseModel):
    id: int 
    name: str
    email:str
    model_config = ConfigDict(from_attributes=True)

class LoansCreate(BaseModel):
    book_id: int 

class LoansOut(BaseModel):
    id: int
    user_id: int
    book_id: int 
    borrowed_at: datetime
    due_at: datetime
    returned_at: Optional[datetime]  = None
    late_fee :  int
    model_config = ConfigDict(from_attributes=True)

ph = PasswordHash.recommended()
app = FastAPI()
bearer = HTTPBearer()  #need to understand 

#Functons


    
def current_user(creds:HTTPAuthorizationCredentials=Depends(bearer), db:Session=Depends(get_session)):
    token = creds.credentials #need to understand
    try: 
        payload = read_token(token)
        user_id = payload["sub"] 
    except Exception:
        raise HTTPException(status_code=401, detail= "Invalid credintals")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Invalid token")
    return user                                                


@app.get("/authors", response_model=list[AuthorOut])
def get_authors(session:Session= Depends(get_session)):
    authors = session.query(Author).all()
    return authors

@app.get("/authors/{author_id}/books",response_model=list[BookOut])
def get_author_books(author_id:int,session: Session=Depends(get_session) ):
    #books = session.get(BookOut, author_id)
    author = session.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="No such author")
    return author.books

@app.get("/books", response_model=list[BookOut])
def show_books(title: str|None= None ,session:Session =Depends(get_session)):
    books = session.query(Book)
    if title:
        books = books.filter(Book.title.ilike(f"%{title}%"))
    return books

@app.get("/loans/me", response_model=list[LoansOut])
def my_loans(session:Session=Depends(get_session), user:User= Depends(current_user)):
    loans = session.query(Loan).filter(Loan.user_id == user.id).all()
    return loans

@app.get("/loans/overdue", response_model=list[LoansOut])
def overdue_loans(session:Session=Depends(get_session), user:User=Depends(current_user)):
    user_loan = session.query(Loan).filter(Loan.user_id == user.id,Loan.returned_at.is_(None) ,Loan.due_at < datetime.now()).all()
    return user_loan


@app.post("/users", response_model= UserOut)
def  create_user(user:UserCreate, session:Session = Depends(get_session)):
    hash = ph.hash(user.password)
    new_user = User(name = user.name, email = user.email, password = hash)
    session.add(new_user)
    try: 
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    session.refresh(new_user)
    return new_user


@app.post("/login")
def login(login:LogIn, session:Session = Depends(get_session)):
    login.email = login.email.lower()
    user = session.query(User).filter(User.email == login.email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credintals")
    if not ph.verify(login.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credintals")
    token = create_token(user.id)
    return  {"access_token":token , "token type": "bearer"}
    

@app.post("/loans/borrow", response_model=LoansOut ,status_code=201)
def borrow_book(loan: LoansCreate, session:Session = Depends(get_session), user:User=Depends(current_user)):
    book_ex = session.get(Book, loan.book_id)
    if book_ex is None:
        raise HTTPException(status_code=404, detail="Book does not exist")
    db_loan = session.query(Loan).filter(Loan.book_id == loan.book_id, Loan.returned_at.is_(None)).first()
    if db_loan:
        raise HTTPException(status_code=409, detail="This book already taken")
    
    new_loan = Loan( user_id = user.id ,book_id = loan.book_id)
    session.add(new_loan)
    session.commit()
    session.refresh(new_loan)
    return new_loan

@app.post("/loans/return", response_model= LoansOut)
def return_book(loan:LoansCreate, session:Session = Depends(get_session), user:User=Depends(current_user)):
    db_loan = session.query(Loan).filter(Loan.book_id == loan.book_id, Loan.user_id == user.id, Loan.returned_at.is_(None)).first()
    if  not db_loan:
        raise HTTPException(status_code=404, detail="No such loan or invalid credintals")
    db_loan.returned_at = datetime.now()
    days_late = (db_loan.returned_at - db_loan.due_at).days
    if days_late >0:
        db_loan.late_fee = days_late*200    
    session.commit()
    session.refresh(db_loan)
    return db_loan    


@app.post("/books", response_model=BookOut, status_code=201)
def add_book(book:BookCreate,session: Session =Depends(get_session), user:User= Depends(current_user)):
    author_ex = session.get(Author, book.author_id)
    if not author_ex: 
        raise HTTPException(status_code=404, detail="No such Author")
    existing = session.query(Book).filter(Book.title == book.title, Book.author_id == book.author_id ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Book already exists")
    new_book = Book(title = book.title, author_id = book.author_id)
    session.add(new_book)
    session.commit()
    session.refresh(new_book)
    return new_book

@app.post("/authors", response_model=AuthorOut, status_code=201)
def add_author(author:AuthorIn, session:Session= Depends(get_session), user:User= Depends(current_user)):
    author_ex = session.query(Author).filter(Author.name ==  author.name).first()
    if author_ex:
        raise HTTPException(status_code=409 , detail="Author already exists")
    new_author = Author(name = author.name)
    session.add(new_author)
    session.commit()
    session.refresh(new_author)
    return new_author

