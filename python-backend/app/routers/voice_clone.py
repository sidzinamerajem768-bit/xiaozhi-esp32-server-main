"""
音色克隆路由模块
对应Java的VoiceCloneController.java
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/voiceClone", tags=["音色克隆管理"])


# ========================================
# 分页查询音色资源
# Migrated from Java: VoiceCloneController.page @ GET /voiceClone
# ========================================
@router.get("")
async def page_voice_clone(
    page: int = Query(1), limit: int = Query(10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分页查询音色资源 对应Java VoiceCloneController.page"""
    from sqlalchemy import text
    offset = (page - 1) * limit
    total = db.execute(text("SELECT COUNT(*) FROM ai_voice_clone WHERE user_id = :uid"), {"uid": current_user.id}).scalar()
    result = db.execute(
        text("SELECT * FROM ai_voice_clone WHERE user_id = :uid ORDER BY create_date DESC LIMIT :lim OFFSET :off"),
        {"uid": current_user.id, "lim": limit, "off": offset}
    ).fetchall()
    items = []
    for row in result:
        d = dict(row._mapping)
        d["hasVoice"] = d.get("voice") is not None
        d.pop("voice", None)
        items.append(d)
    return {"code": 0, "msg": "success", "data": {"list": items, "total": total, "page": page, "limit": limit}}


# ========================================
# 上传音频进行声音克隆
# Migrated from Java: VoiceCloneController.uploadVoice @ POST /voiceClone/upload
# ========================================
@router.post("/upload")
async def upload_voice(
    id: str = Query(...), voiceFile: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传音频克隆 对应Java VoiceCloneController.uploadVoice"""
    if not voiceFile.content_type or not voiceFile.content_type.startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只允许上传音频文件")
    ext = voiceFile.filename.split(".")[-1].lower() if voiceFile.filename else ""
    if ext not in ["mp3", "wav"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只允许上传.mp3和.wav格式的文件")
    content = await voiceFile.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件大小不能超过10MB")
    from sqlalchemy import text
    existing = db.execute(text("SELECT * FROM ai_voice_clone WHERE id = :id"), {"id": id}).first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    existing_dict = dict(existing._mapping)
    if existing_dict.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限操作")
    db.execute(text("UPDATE ai_voice_clone SET voice = :voice WHERE id = :id"), {"voice": content, "id": id})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 更新声音克隆名称
# Migrated from Java: VoiceCloneController.updateName @ POST /voiceClone/updateName
# ========================================
@router.post("/updateName")
async def update_voice_name(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新克隆名称 对应Java VoiceCloneController.updateName"""
    from sqlalchemy import text
    vid = body.get("id")
    name = body.get("name")
    if not vid or not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="参数不完整")
    existing = db.execute(text("SELECT * FROM ai_voice_clone WHERE id = :id"), {"id": vid}).first()
    if not existing or dict(existing._mapping).get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限操作")
    db.execute(text("UPDATE ai_voice_clone SET name = :name WHERE id = :id"), {"name": name, "id": vid})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 获取音频下载ID
# Migrated from Java: VoiceCloneController.getAudioId @ POST /voiceClone/audio/{id}
# ========================================
@router.post("/audio/{id}")
async def get_audio_id(
    id: str, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取音频下载ID 对应Java VoiceCloneController.getAudioId"""
    from sqlalchemy import text
    existing = db.execute(text("SELECT * FROM ai_voice_clone WHERE id = :id"), {"id": id}).first()
    if not existing or dict(existing._mapping).get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限操作")
    download_uuid = str(uuid.uuid4())
    return {"code": 0, "msg": "success", "data": download_uuid}


# ========================================
# 播放音频
# Migrated from Java: VoiceCloneController.playVoice @ GET /voiceClone/play/{uuid}
# ========================================
@router.get("/play/{uuid}")
async def play_voice(uuid: str):
    """播放音频 对应Java VoiceCloneController.playVoice"""
    return Response(status_code=status.HTTP_404_NOT_FOUND)


# ========================================
# 复刻音频
# Migrated from Java: VoiceCloneController.cloneAudio @ POST /voiceClone/cloneAudio
# ========================================
@router.post("/cloneAudio")
async def clone_audio(
    body: dict, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """复刻音频 对应Java VoiceCloneController.cloneAudio"""
    clone_id = body.get("cloneId")
    if not clone_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="参数不完整")
    from sqlalchemy import text
    existing = db.execute(text("SELECT * FROM ai_voice_clone WHERE id = :id"), {"id": clone_id}).first()
    if not existing or dict(existing._mapping).get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限操作")
    return {"code": 0, "msg": "success", "data": None}