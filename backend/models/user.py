from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class User(BaseModel):
    openid: str
    nickname: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    last_login: datetime = datetime.utcnow()
    work_records: Dict[str, Any] = {}  # 格式: {"日期": {"accumulated_time": int, "is_running": bool, "start_time": float}}

class VerificationCode(BaseModel):
    code: str
    openid: str
    created_at: datetime = datetime.utcnow()
    expires_at: datetime
    used: bool = False 