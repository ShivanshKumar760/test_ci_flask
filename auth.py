import jwt 
import bcrypt 
import os
from functools import wraps
from flask import request,jsonify
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET","jwtsecret")
JWT_ALGO = "HS256"
JWT_EXPIRES = 24*60*60 # 24 hours in second 

#--- Password Helpers

def hash_password(plain:str)-> str:
    return bcrypt.hashpw(plain.encode(),bcrypt.gensalt()).decode()

def check_password(plain:str,hashed:str)->bool:
    return bcrypt.checkpw(plain.encode(),hashed.encode())

def create_token(user_id:int,username:str)->str:
    import time
    payload = {
        "user_id": user_id,
        "username" : username,
        "exp": int(time.time()) + JWT_EXPIRES,
    }

    return jwt.encode(payload,JWT_SECRET,algorithm=JWT_ALGO)

def decode_token(token:str)->str:
    return jwt.decode(token,JWT_SECRET,algorithms=[JWT_ALGO])


def login_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        from flask import g
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error":"Missing or malformed Authorization header"}),401
        token = header[len("Bearer "):]
        try:
            payload = decode_token(token)
            g.user_id=payload["user_id"]
            g.username=payload["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error:Token expired"}),401
        except jwt.InvalidTokenError:
            return jsonify({"error":"Invalid token"}),401
        return f(*args,**kwargs)
    return decorated