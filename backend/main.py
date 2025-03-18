from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from api.wechat import router as wechat_router
from api.auth import router as auth_router
from api.sync import router as sync_router
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="Pimer Backend")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(wechat_router, prefix="/api/wechat", tags=["wechat"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(sync_router, prefix="/api/sync", tags=["sync"])

@app.get("/")
async def root():
    return {"message": "Welcome to Pimer Backend!"} 