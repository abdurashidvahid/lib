from jose import jwt
from datetime import datetime,timedelta,timezone
import os
from dotenv import load_dotenv
load_dotenv("key.env")
alg = "HS256"
sec_key = os.getenv("MY_WORLD")
def create_token(user_id):
    payload = {"sub":str(user_id),"exp":datetime.now(timezone.utc) + timedelta(minutes=3600)}
    token = jwt.encode(payload,sec_key,alg)
    return token
def read_token(token):
    detoken = jwt.decode(token,sec_key,algorithms=[alg])
    return detoken
