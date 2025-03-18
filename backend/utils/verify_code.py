import random
import string
from datetime import datetime, timedelta
from typing import Tuple
from models.user import VerificationCode

def generate_verification_code(openid: str, expires_minutes: int = 5) -> Tuple[str, VerificationCode]:
    """
    生成验证码
    :param openid: 用户的 OpenID
    :param expires_minutes: 验证码有效期（分钟）
    :return: (验证码字符串, 验证码对象)
    """
    code = ''.join(random.choices(string.digits, k=6))
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
    
    verification = VerificationCode(
        code=code,
        openid=openid,
        expires_at=expires_at
    )
    
    return code, verification

def is_code_valid(stored_code: VerificationCode, input_code: str) -> bool:
    """
    验证验证码是否有效
    :param stored_code: 存储的验证码对象
    :param input_code: 用户输入的验证码
    :return: 是否有效
    """
    if stored_code.used:
        return False
        
    if datetime.utcnow() > stored_code.expires_at:
        return False
        
    return stored_code.code == input_code 