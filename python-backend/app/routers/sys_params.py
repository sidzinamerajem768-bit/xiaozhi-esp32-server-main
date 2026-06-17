"""
参数管理路由模块
对应Java的SysParamsController.java
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/admin/params", tags=["参数管理"])

def check_super_admin(user: User):
    from fastapi import HTTPException, status
    if user.super_admin != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可操作")


# ========================================
# 分页查询参数
# Migrated from Java: SysParamsController.page @ GET /admin/params/page
# ========================================
@router.get("/page")
async def page_params(
    paramCode: Optional[str] = Query(None), page: int = Query(1), limit: int = Query(10),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """分页查询参数 对应Java SysParamsController.page"""
    check_super_admin(current_user)
    offset = (page - 1) * limit
    where = ""
    params = {"lim": limit, "off": offset}
    if paramCode:
        where = "WHERE param_code LIKE :pc OR param_remark LIKE :pr"
        params["pc"] = f"%{paramCode}%"
        params["pr"] = f"%{paramCode}%"
    total = db.execute(text(f"SELECT COUNT(*) FROM sys_params {where}"), params).scalar()
    result = db.execute(text(f"SELECT * FROM sys_params {where} ORDER BY id ASC LIMIT :lim OFFSET :off"), params).fetchall()
    items = [dict(r._mapping) for r in result]
    return {"code": 0, "msg": "success", "data": {"list": items, "total": total, "page": page, "limit": limit}}


# ========================================
# 获取参数详情
# Migrated from Java: SysParamsController.get @ GET /admin/params/{id}
# ========================================
@router.get("/{id}")
async def get_param(
    id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取参数详情 对应Java SysParamsController.get"""
    check_super_admin(current_user)
    result = db.execute(text("SELECT * FROM sys_params WHERE id = :id"), {"id": id}).first()
    if not result:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="参数不存在")
    return {"code": 0, "msg": "success", "data": dict(result._mapping)}


# ========================================
# 保存参数
# Migrated from Java: SysParamsController.save @ POST /admin/params
# ========================================
@router.post("")
async def save_param(
    body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """保存参数 对应Java SysParamsController.save"""
    check_super_admin(current_user)
    from datetime import datetime
    db.execute(
        text("INSERT INTO sys_params (param_code, param_value, param_type, param_remark, creator, create_date) VALUES (:pc, :pv, :pt, :pr, :c, :cd)"),
        {"pc": body.get("paramCode"), "pv": body.get("paramValue"), "pt": body.get("paramType", "0"),
         "pr": body.get("paramRemark", ""), "c": current_user.id, "cd": datetime.now()}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 修改参数
# Migrated from Java: SysParamsController.update @ PUT /admin/params
# ========================================
@router.put("")
async def update_param(
    body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """修改参数 对应Java SysParamsController.update"""
    check_super_admin(current_user)
    db.execute(
        text("UPDATE sys_params SET param_value = :pv, param_remark = :pr WHERE id = :id"),
        {"pv": body.get("paramValue"), "pr": body.get("paramRemark", ""), "id": body.get("id")}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 删除参数
# Migrated from Java: SysParamsController.delete @ POST /admin/params/delete
# ========================================
@router.post("/delete")
async def delete_params(
    ids: list[str], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除参数 对应Java SysParamsController.delete"""
    check_super_admin(current_user)
    for sid in ids:
        db.execute(text("DELETE FROM sys_params WHERE id = :id"), {"id": int(sid)})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}