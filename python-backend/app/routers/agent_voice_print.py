"""
声纹管理路由模块
对应Java的AgentVoicePrintController.java
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, exc as sa_exc
from datetime import datetime
import uuid as uid_mod
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/agent/voice-print", tags=["声纹管理"])


def _safe_db(sql, params, db):
    try:
        return db.execute(text(sql), params)
    except sa_exc.ProgrammingError:
        db.rollback()
        return None
    except Exception:
        db.rollback()
        return None


def _safe_list(sql, params, db):
    try:
        return db.execute(text(sql), params).fetchall()
    except sa_exc.ProgrammingError:
        db.rollback()
        return []
    except Exception:
        db.rollback()
        return []


@router.post("")
async def create_voice_print(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _safe_db("INSERT INTO ai_agent_voice_print (id, agent_id, voice_print_name, creator, create_date) VALUES (:id, :aid, :vn, :c, :cd)", {"id": str(uid_mod.uuid4()), "aid": body.get("agentId"), "vn": body.get("voicePrintName"), "c": current_user.id, "cd": datetime.now()}, db)
    if r is not None: db.commit()
    return {"code": 0, "msg": "success", "data": None}


@router.put("")
async def update_voice_print(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _safe_db("UPDATE ai_agent_voice_print SET voice_print_name = :vn WHERE id = :id AND creator = :c", {"vn": body.get("voicePrintName"), "id": body.get("id"), "c": current_user.id}, db)
    if r is not None: db.commit()
    return {"code": 0, "msg": "success", "data": None}


@router.delete("/{id}")
async def delete_voice_print(id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _safe_db("DELETE FROM ai_agent_voice_print WHERE id = :id AND creator = :c", {"id": id, "c": current_user.id}, db)
    if r is not None: db.commit()
    return {"code": 0, "msg": "success", "data": None}


@router.get("/list/{id}")
async def list_voice_prints(id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _safe_list("SELECT id, agent_id, voice_print_name FROM ai_agent_voice_print WHERE creator = :c AND agent_id = :aid", {"c": current_user.id, "aid": id}, db)
    items = [dict(r._mapping) for r in rows]
    return {"code": 0, "msg": "success", "data": items}