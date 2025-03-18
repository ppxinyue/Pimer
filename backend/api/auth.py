from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
import os
import jwt
from typing import Optional
import pymongo
from models.user import User
from utils.verify_code import is_code_valid

router = APIRouter()

# MongoDB 连接
MONGO_URI = os.getenv("MONGODB_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client.pimer
users = db.users
verification_codes = db.verification_codes

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

class VerifyCodeRequest(BaseModel):
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(data: dict) -> str:
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(token: str) -> Optional[User]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_data = users.find_one({"openid": payload["sub"]})
        if user_data:
            return User(**user_data)
    except:
        return None
    return None

@router.post("/verify", response_model=TokenResponse)
async def verify_code(request: VerifyCodeRequest):
    """验证登录验证码"""
    # 查找最新的未使用验证码
    stored_code = verification_codes.find_one(
        {"used": False},
        sort=[("created_at", pymongo.DESCENDING)]
    )
    
    if not stored_code or not is_code_valid(stored_code, request.code):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    
    # 标记验证码为已使用
    verification_codes.update_one(
        {"_id": stored_code["_id"]},
        {"$set": {"used": True}}
    )
    
    # 获取或创建用户
    user_data = users.find_one({"openid": stored_code["openid"]})
    if not user_data:
        user = User(openid=stored_code["openid"])
        users.insert_one(user.dict())
    else:
        user = User(**user_data)
        users.update_one(
            {"openid": user.openid},
            {"$set": {"last_login": datetime.utcnow()}}
        )
    
    # 生成访问令牌
    access_token = create_access_token({"sub": user.openid})
    return TokenResponse(access_token=access_token) 