from fastapi import APIRouter, HTTPException, Header
from typing import Dict, Any, Optional
from datetime import datetime
import pymongo
import os
from models.user import User
from .auth import get_current_user

router = APIRouter()

# MongoDB 连接
MONGO_URI = os.getenv("MONGODB_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client.pimer
users = db.users

@router.post("/work_records")
async def sync_work_records(
    work_records: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    """同步工作记录"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user = await get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 更新用户的工作记录
    users.update_one(
        {"openid": user.openid},
        {"$set": {
            "work_records": work_records,
            "last_sync": datetime.utcnow()
        }}
    )
    
    return {"status": "success"}

@router.get("/work_records")
async def get_work_records(
    authorization: Optional[str] = Header(None)
):
    """获取工作记录"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user = await get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"work_records": user.work_records} 