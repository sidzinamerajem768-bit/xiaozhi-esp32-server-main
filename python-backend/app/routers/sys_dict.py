"""
字典数据管理路由模块
对应Java的SysDictDataController.java
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/admin/dict/data", tags=["字典数据管理"])

def check_super_admin(user: User):
    from fastapi import HTTPException, status
    if user.super_admin != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可操作")


# ========================================
# 分页查询字典数据
# Migrated from Java: SysDictDataController.page @ GET /admin/dict/data/page
# ========================================
@router.get("/page")
async def page_dict_data(
    dictTypeId: str = Query(...), dictLabel: Optional[str] = Query(None),
    dictValue: Optional[str] = Query(None), page: int = Query(1), limit: int = Query(10),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """分页查询字典数据 对应Java SysDictDataController.page"""
    check_super_admin(current_user)
    offset = (page - 1) * limit
    where = "WHERE dict_type_id = :dtid"
    params = {"dtid": dictTypeId, "lim": limit, "off": offset}
    if dictLabel:
        where += " AND dict_label LIKE :dl"
        params["dl"] = f"%{dictLabel}%"
    if dictValue:
        where += " AND dict_value LIKE :dv"
        params["dv"] = f"%{dictValue}%"
    total = db.execute(text(f"SELECT COUNT(*) FROM sys_dict_data {where}"), params).scalar()
    result = db.execute(text(f"SELECT * FROM sys_dict_data {where} ORDER BY sort ASC LIMIT :lim OFFSET :off"), params).fetchall()
    items = [dict(r._mapping) for r in result]
    return {"code": 0, "msg": "success", "data": {"list": items, "total": total, "page": page, "limit": limit}}


# ========================================
# 获取字典数据详情
# Migrated from Java: SysDictDataController.get @ GET /admin/dict/data/{id}
# ========================================
@router.get("/{id}")
async def get_dict_data(
    id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取字典数据详情 对应Java SysDictDataController.get"""
    check_super_admin(current_user)
    result = db.execute(text("SELECT * FROM sys_dict_data WHERE id = :id"), {"id": id}).first()
    if not result:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字典数据不存在")
    return {"code": 0, "msg": "success", "data": dict(result._mapping)}


# ========================================
# 新增字典数据
# Migrated from Java: SysDictDataController.save @ POST /admin/dict/data/save
# ========================================
@router.post("/save")
async def save_dict_data(
    body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """新增字典数据 对应Java SysDictDataController.save"""
    check_super_admin(current_user)
    from datetime import datetime
    db.execute(
        text("INSERT INTO sys_dict_data (dict_type_id, dict_label, dict_value, sort, creator, create_date) VALUES (:dtid, :dl, :dv, :st, :c, :cd)"),
        {"dtid": body.get("dictTypeId"), "dl": body.get("dictLabel"), "dv": body.get("dictValue"),
         "st": body.get("sort", 0), "c": current_user.id, "cd": datetime.now()}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 修改字典数据
# Migrated from Java: SysDictDataController.update @ PUT /admin/dict/data/update
# ========================================
@router.put("/update")
async def update_dict_data(
    body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """修改字典数据 对应Java SysDictDataController.update"""
    check_super_admin(current_user)
    db.execute(
        text("UPDATE sys_dict_data SET dict_label = :dl, dict_value = :dv, sort = :st WHERE id = :id"),
        {"dl": body.get("dictLabel"), "dv": body.get("dictValue"), "st": body.get("sort", 0), "id": body.get("id")}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 删除字典数据
# Migrated from Java: SysDictDataController.delete @ POST /admin/dict/data/delete
# ========================================
@router.post("/delete")
async def delete_dict_data(
    ids: list[int], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除字典数据 对应Java SysDictDataController.delete"""
    check_super_admin(current_user)
    for sid in ids:
        db.execute(text("DELETE FROM sys_dict_data WHERE id = :id"), {"id": sid})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 获取字典数据列表（按类型）
# Migrated from Java: SysDictDataController.getDictDataByType @ GET /admin/dict/data/type/{dictType}
# ========================================
@router.get("/type/{dictType}")
async def get_dict_data_by_type(
    dictType: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取字典数据列表 对应Java SysDictDataController.getDictDataByType"""
    result = db.execute(
        text("SELECT id, dict_label as dictLabel, dict_value as dictValue, sort FROM sys_dict_data WHERE dict_type_id = :dt ORDER BY sort ASC"),
        {"dt": dictType}
    ).fetchall()
    items = [dict(r._mapping) for r in result]
    return {"code": 0, "msg": "success", "data": items}