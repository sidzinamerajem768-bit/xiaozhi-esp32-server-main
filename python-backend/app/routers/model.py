"""
模型配置路由模块
对应Java的ModelController.java
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/models", tags=["模型配置"])


# ========================================
# 获取模型名称列表
# Migrated from Java: ModelController.getModelNames @ GET /models/names
# ========================================
@router.get("/names")
async def get_model_names(
    modelType: str = Query(...),
    modelName: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模型名称列表 对应Java ModelController.getModelNames"""
    from sqlalchemy import text
    query = "SELECT id, model_name, model_type, provide_code FROM ai_model_config WHERE model_type = :mt"
    params = {"mt": modelType}
    if modelName:
        query += " AND model_name LIKE :mn"
        params["mn"] = f"%{modelName}%"
    result = db.execute(text(query), params).fetchall()
    models = [dict(row._mapping) for row in result]
    return {"code": 0, "msg": "success", "data": models}


# ========================================
# 获取LLM模型信息
# Migrated from Java: ModelController.getLlmModelCodeList @ GET /models/llm/names
# ========================================
@router.get("/llm/names")
async def get_llm_model_names(
    modelName: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取LLM模型信息 对应Java ModelController.getLlmModelCodeList"""
    from sqlalchemy import text
    query = "SELECT id, model_name, model_type FROM ai_model_config WHERE model_type = 'llm'"
    params = {}
    if modelName:
        query += " AND model_name LIKE :mn"
        params["mn"] = f"%{modelName}%"
    result = db.execute(text(query), params).fetchall()
    models = [dict(row._mapping) for row in result]
    return {"code": 0, "msg": "success", "data": models}


# ========================================
# 获取模型音色列表
# Migrated from Java: ModelController.getVoiceList @ GET /models/{modelId}/voices
# ========================================
@router.get("/{modelId}/voices")
async def get_voice_list(
    modelId: str,
    voiceName: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模型音色 对应Java ModelController.getVoiceList"""
    from sqlalchemy import text
    query = "SELECT id, voice_name, voice_id, language FROM ai_timbre WHERE model_id = :mid"
    params = {"mid": modelId}
    if voiceName:
        query += " AND voice_name LIKE :vn"
        params["vn"] = f"%{voiceName}%"
    result = db.execute(text(query), params).fetchall()
    voices = [dict(row._mapping) for row in result]
    return {"code": 0, "msg": "success", "data": voices}