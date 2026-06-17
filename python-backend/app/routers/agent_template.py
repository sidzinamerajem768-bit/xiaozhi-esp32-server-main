"""
智能体模板管理路由模块
对应Java的AgentTemplateController.java
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/agent/template", tags=["智能体模板管理"])

def check_super_admin(user: User):
    from fastapi import HTTPException, status
    if user.super_admin != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可操作")


# ========================================
# 获取模板分页列表
# Migrated from Java: AgentTemplateController.getAgentTemplatesPage @ GET /agent/template/page
# ========================================
@router.get("/page")
async def page_templates(
    agentName: Optional[str] = Query(None), page: int = Query(1), limit: int = Query(10),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取模板分页列表 对应Java AgentTemplateController.getAgentTemplatesPage"""
    check_super_admin(current_user)
    offset = (page - 1) * limit
    where = ""
    params = {"lim": limit, "off": offset}
    if agentName:
        where = "WHERE agent_name LIKE :an"
        params["an"] = f"%{agentName}%"
    total = db.execute(text(f"SELECT COUNT(*) FROM ai_agent_template {where}"), params).scalar()
    result = db.execute(text(f"SELECT * FROM ai_agent_template {where} ORDER BY sort ASC LIMIT :lim OFFSET :off"), params).fetchall()
    items = [dict(r._mapping) for r in result]
    return {"code": 0, "msg": "success", "data": {"list": items, "total": total, "page": page, "limit": limit}}


# ========================================
# 获取模板详情
# Migrated from Java: AgentTemplateController.getAgentTemplateById @ GET /agent/template/{id}
# ========================================
@router.get("/{id}")
async def get_template(
    id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取模板详情 对应Java AgentTemplateController.getAgentTemplateById"""
    check_super_admin(current_user)
    result = db.execute(text("SELECT * FROM ai_agent_template WHERE id = :id"), {"id": id}).first()
    if not result:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return {"code": 0, "msg": "success", "data": dict(result._mapping)}


# ========================================
# 创建模板
# Migrated from Java: AgentTemplateController.createAgentTemplate @ POST /agent/template
# ========================================
@router.post("")
async def create_template(
    body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """创建模板 对应Java AgentTemplateController.createAgentTemplate"""
    check_super_admin(current_user)
    import uuid
    tid = str(uuid.uuid4())
    max_sort = db.execute(text("SELECT COALESCE(MAX(sort), 0) + 1 FROM ai_agent_template")).scalar()
    db.execute(
        text("""
            INSERT INTO ai_agent_template (id, agent_name, system_prompt, sort, creator, created_at)
            VALUES (:id, :an, :sp, :st, :c, :cd)
        """),
        {"id": tid, "an": body.get("agentName", ""), "sp": body.get("systemPrompt", ""),
         "st": body.get("sort", max_sort), "c": current_user.id, "cd": datetime.now()}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": {"id": tid}}


# ========================================
# 更新模板
# Migrated from Java: AgentTemplateController.updateAgentTemplate @ PUT /agent/template
# ========================================
@router.put("")
async def update_template(
    body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """更新模板 对应Java AgentTemplateController.updateAgentTemplate"""
    check_super_admin(current_user)
    db.execute(
        text("UPDATE ai_agent_template SET agent_name = :an, system_prompt = :sp, sort = :st WHERE id = :id"),
        {"an": body.get("agentName"), "sp": body.get("systemPrompt"), "st": body.get("sort"), "id": body.get("id")}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 删除模板
# Migrated from Java: AgentTemplateController.deleteAgentTemplate @ DELETE /agent/template/{id}
# ========================================
@router.delete("/{id}")
async def delete_template(
    id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除模板 对应Java AgentTemplateController.deleteAgentTemplate"""
    check_super_admin(current_user)
    db.execute(text("DELETE FROM ai_agent_template WHERE id = :id"), {"id": id})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 批量删除模板
# Migrated from Java: AgentTemplateController.batchRemoveAgentTemplates @ POST /agent/template/batch-remove
# ========================================
@router.post("/batch-remove")
async def batch_remove_templates(
    ids: list[str], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """批量删除模板 对应Java AgentTemplateController.batchRemoveAgentTemplates"""
    check_super_admin(current_user)
    for tid in ids:
        db.execute(text("DELETE FROM ai_agent_template WHERE id = :id"), {"id": tid})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}