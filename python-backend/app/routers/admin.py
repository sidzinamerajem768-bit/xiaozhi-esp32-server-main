"""
管理员管理路由模块
对应Java的AdminController.java
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/admin", tags=["管理员管理"])


def check_super_admin(current_user: User):
    """检查是否为超级管理员"""
    if current_user.super_admin != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可操作")


# ========================================
# 分页查找用户
# Migrated from Java: AdminController.pageUser @ GET /admin/users
# ========================================
@router.get("/users")
async def page_users(
    mobile: Optional[str] = Query(None), page: int = Query(1), limit: int = Query(10),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """分页查找用户 对应Java AdminController.pageUser"""
    check_super_admin(current_user)
    offset = (page - 1) * limit
    where = ""
    params = {"lim": limit, "off": offset}
    if mobile:
        where = "WHERE username LIKE :mobile"
        params["mobile"] = f"%{mobile}%"
    total = db.execute(text(f"SELECT COUNT(*) FROM sys_user {where}"), params).scalar()
    result = db.execute(text(f"SELECT id, username, status, super_admin as superAdmin, create_date FROM sys_user {where} ORDER BY id DESC LIMIT :lim OFFSET :off"), params).fetchall()
    items = [dict(r._mapping) for r in result]
    return {"code": 0, "msg": "success", "data": {"list": items, "total": total, "page": page, "limit": limit}}


# ========================================
# 重置密码
# Migrated from Java: AdminController.update @ PUT /admin/users/{id}
# ========================================
@router.put("/users/{id}")
async def reset_password(
    id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """重置密码 对应Java AdminController.update"""
    check_super_admin(current_user)
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"])
    new_pwd = "123456"
    db.execute(text("UPDATE sys_user SET password = :pw WHERE id = :id"), {"pw": pwd.hash(new_pwd), "id": id})
    db.commit()
    return {"code": 0, "msg": "success", "data": new_pwd}


# ========================================
# 删除用户
# Migrated from Java: AdminController.delete @ DELETE /admin/users/{id}
# ========================================
@router.delete("/users/{id}")
async def delete_user(
    id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除用户 对应Java AdminController.delete"""
    check_super_admin(current_user)
    db.execute(text("DELETE FROM sys_user WHERE id = :id"), {"id": id})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 批量修改用户状态
# Migrated from Java: AdminController.changeStatus @ PUT /admin/users/changeStatus/{status}
# ========================================
@router.put("/users/changeStatus/{status}")
async def change_user_status(
    status: int, userIds: list[str], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """批量修改用户状态 对应Java AdminController.changeStatus"""
    check_super_admin(current_user)
    for uid in userIds:
        db.execute(text("UPDATE sys_user SET status = :st WHERE id = :id"), {"st": status, "id": int(uid)})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 分页查找设备
# Migrated from Java: AdminController.pageDevice @ GET /admin/device/all
# ========================================
@router.get("/device/all")
async def page_devices(
    keywords: Optional[str] = Query(None), page: int = Query(1), limit: int = Query(10),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """分页查找设备 对应Java AdminController.pageDevice"""
    check_super_admin(current_user)
    offset = (page - 1) * limit
    where = ""
    params = {"lim": limit, "off": offset}
    if keywords:
        where = "WHERE mac_address LIKE :kw OR alias LIKE :kw2"
        params["kw"] = f"%{keywords}%"
        params["kw2"] = f"%{keywords}%"
    total = db.execute(text(f"SELECT COUNT(*) FROM ai_device {where}"), params).scalar()
    result = db.execute(text(f"SELECT * FROM ai_device {where} ORDER BY create_date DESC LIMIT :lim OFFSET :off"), params).fetchall()
    items = [dict(r._mapping) for r in result]
    return {"code": 0, "msg": "success", "data": {"list": items, "total": total, "page": page, "limit": limit}}