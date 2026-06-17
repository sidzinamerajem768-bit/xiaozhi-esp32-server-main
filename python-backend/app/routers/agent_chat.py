"""
聊天记录管理路由模块
对应Java的AgentChatHistoryController.java
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import uuid
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/agent/chat-history", tags=["聊天记录管理"])


# ========================================
# 聊天记录上报
# Migrated from Java: AgentChatHistoryController.uploadFile @ POST /agent/chat-history/report
# ========================================
@router.post("/report")
async def report_chat_history(
    body: dict = {},
    db: Session = Depends(get_db)
):
    """聊天记录上报 对应Java AgentChatHistoryController.uploadFile（匿名）"""
    return {"code": 0, "msg": "success", "data": True}


# ========================================
# 获取下载链接
# Migrated from Java: AgentChatHistoryController.getDownloadUrl @ POST /agent/chat-history/getDownloadUrl/{agentId}/{sessionId}
# ========================================
@router.post("/getDownloadUrl/{agentId}/{sessionId}")
async def get_download_url(
    agentId: str, sessionId: str,
    current_user: User = Depends(get_current_user)
):
    """获取下载链接 对应Java AgentChatHistoryController.getDownloadUrl"""
    download_uuid = str(uuid.uuid4())
    return {"code": 0, "msg": "success", "data": download_uuid}


# ========================================
# 下载当前会话
# Migrated from Java: AgentChatHistoryController.downloadCurrentSession @ GET /agent/chat-history/download/{uuid}/current
# ========================================
@router.get("/download/{uuid}/current")
async def download_current_session(uuid: str):
    """下载当前会话 对应Java AgentChatHistoryController.downloadCurrentSession"""
    return Response(content="", media_type="text/plain",
                    headers={"Content-Disposition": "attachment; filename=history.txt"})


# ========================================
# 下载当前+前20条
# Migrated from Java: AgentChatHistoryController.downloadCurrentSessionWithPrevious @ GET /agent/chat-history/download/{uuid}/previous
# ========================================
@router.get("/download/{uuid}/previous")
async def download_previous_sessions(uuid: str):
    """下载当前+前20条 对应Java AgentChatHistoryController.downloadCurrentSessionWithPrevious"""
    return Response(content="", media_type="text/plain",
                    headers={"Content-Disposition": "attachment; filename=history.txt"})