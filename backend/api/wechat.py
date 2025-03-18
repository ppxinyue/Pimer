from fastapi import APIRouter, Request, Response
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy import parse_message, create_reply
from wechatpy.messages import TextMessage
import os
from utils.verify_code import generate_verification_code
from typing import Optional
import pymongo
from datetime import datetime

router = APIRouter()

# MongoDB 连接
MONGO_URI = os.getenv("MONGODB_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client.pimer
verification_codes = db.verification_codes

@router.get("/")
async def wechat_verify(signature: str, timestamp: str, nonce: str, echostr: str):
    """微信服务器验证接口"""
    token = os.getenv("WECHAT_TOKEN")
    try:
        check_signature(token, signature, timestamp, nonce)
        return Response(content=echostr, media_type="text/plain")
    except InvalidSignatureException:
        return Response(status_code=403)

@router.post("/")
async def wechat_handler(request: Request):
    """处理微信消息"""
    token = os.getenv("WECHAT_TOKEN")
    body = await request.body()
    try:
        msg = parse_message(body)
        if isinstance(msg, TextMessage):
            if msg.content.lower() == "pimer":
                # 生成验证码
                code, verification = generate_verification_code(msg.source)
                
                # 保存验证码到数据库
                verification_dict = verification.dict()
                verification_codes.insert_one(verification_dict)
                
                # 返回验证码消息
                reply = create_reply(
                    f"您的登录验证码是：{code}\n"
                    f"验证码有效期为5分钟。\n"
                    f"请尽快在应用中输入验证码完成登录。", 
                    msg
                )
            else:
                reply = create_reply("发送 'pimer' 获取登录验证码", msg)
        else:
            reply = create_reply("发送 'pimer' 获取登录验证码", msg)
            
        return Response(content=reply.render(), media_type="application/xml")
    except Exception as e:
        return Response(status_code=500, content=str(e)) 