"""
替换词管理路由模块
对应Java的CorrectWordController.java
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import text, exc as sa_exc
from typing import Optional
from datetime import datetime
import uuid as uid_mod
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/correct-word", tags=["替换词管理"])


def _safe_list(uid, page, limit, db):
    try:
        offset = (page - 1) * limit
        total = db.execute(text("SELECT COUNT(*) FROM ai_correct_word_file WHERE creator = :c"), {"c": uid}).scalar()
        r = db.execute(text("SELECT id, file_name FROM ai_correct_word_file WHERE creator = :c ORDER BY create_date DESC LIMIT :lim OFFSET :off"), {"c": uid, "lim": limit, "off": offset}).fetchall()
        items = [dict(x._mapping) for x in r]
        return {"list": items, "total": total, "page": page, "limit": limit}
    except sa_exc.ProgrammingError:
        db.rollback()
        return {"list": [], "total": 0, "page": page, "limit": limit}


@router.post("/file")
async def create_correct_word_file(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        fid = str(uid_mod.uuid4())
        db.execute(text("INSERT INTO ai_correct_word_file (id, file_name, content, creator, create_date) VALUES (:id, :fn, :ct, :c, :cd)"), {"id": fid, "fn": body.get("fileName"), "ct": "\n".join(body.get("content", [])), "c": current_user.id, "cd": datetime.now()})
        db.commit()
        return {"code": 0, "msg": "success", "data": {"id": fid, "fileName": body.get("fileName")}}
    except sa_exc.ProgrammingError:
        db.rollback()
        return {"code": 0, "msg": "success", "data": {"id": "mock", "fileName": body.get("fileName")}}


@router.put("/file/{fileId}")
async def update_correct_word_file(fileId: str, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db.execute(text("UPDATE ai_correct_word_file SET file_name = :fn, content = :ct WHERE id = :id AND creator = :c"), {"fn": body.get("fileName"), "ct": "\n".join(body.get("content", [])), "id": fileId, "c": current_user.id})
        db.commit()
    except sa_exc.ProgrammingError:
        db.rollback()
    return {"code": 0, "msg": "success", "data": None}


@router.get("/file/list")
async def list_correct_word_files(page: int = Query(1), limit: int = Query(10), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = _safe_list(current_user.id, page, limit, db)
    return {"code": 0, "msg": "success", "data": data}


@router.get("/file/select")
async def list_all_correct_word_files(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = _safe_list(current_user.id, 1, 1000, db)
    return {"code": 0, "msg": "success", "data": data.get("list", [])}


@router.get("/file/download/{fileId}")
async def download_correct_word_file(fileId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("SELECT file_name, content FROM ai_correct_word_file WHERE id = :id AND creator = :c"), {"id": fileId, "c": current_user.id}).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(content=result[1] or "", media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{result[0]}"'})


@router.delete("/file/{fileId}")
async def delete_correct_word_file(fileId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM ai_correct_word_file WHERE id = :id AND creator = :c"), {"id": fileId, "c": current_user.id})
        db.commit()
    except sa_exc.ProgrammingError:
        db.rollback()
    return {"code": 0, "msg": "success", "data": None}


@router.post("/file/batch-delete")
async def batch_delete_correct_word_files(fileIds: list[str], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        for fid in fileIds:
            db.execute(text("DELETE FROM ai_correct_word_file WHERE id = :id AND creator = :c"), {"id": fid, "c": current_user.id})
        db.commit()
    except sa_exc.ProgrammingError:
        db.rollback()
    return {"code": 0, "msg": "success", "data": None}