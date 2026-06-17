"""
知识库管理路由模块
对应Java的KnowledgeBaseController.java
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime
import uuid
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/datasets", tags=["知识库管理"])


# ========================================
# 分页查询知识库列表
# Migrated from Java: KnowledgeBaseController.getPageList @ GET /datasets
# ========================================
@router.get("")
async def get_datasets(
    name: Optional[str] = Query(None),
    page: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="page_size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分页查询知识库 对应Java KnowledgeBaseController.getPageList"""
    from sqlalchemy import text
    # 构建查询
    query_str = "SELECT * FROM ai_rag_knowledge_dataset WHERE creator = :creator"
    params = {"creator": current_user.id}
    if name:
        query_str += " AND name LIKE :name"
        params["name"] = f"%{name}%"
    query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    
    result = db.execute(text(query_str), params).fetchall()
    datasets = [dict(row._mapping) for row in result]
    
    return {"code": 0, "msg": "success", "data": {"list": datasets, "total": len(datasets), "page": page, "pageSize": page_size}}


# ========================================
# 根据知识库ID获取详情
# Migrated from Java: KnowledgeBaseController.getByDatasetId @ GET /datasets/{dataset_id}
# ========================================
@router.get("/{dataset_id}")
async def get_dataset_by_id(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取知识库详情 对应Java KnowledgeBaseController.getByDatasetId"""
    from sqlalchemy import text
    result = db.execute(text("SELECT * FROM ai_rag_knowledge_dataset WHERE dataset_id = :id"), {"id": dataset_id}).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    dataset = dict(result._mapping)
    if dataset.get("creator") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限查看该知识库")
    return {"code": 0, "msg": "success", "data": dataset}


# ========================================
# 创建知识库
# Migrated from Java: KnowledgeBaseController.save @ POST /datasets
# ========================================
@router.post("")
async def create_dataset(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建知识库 对应Java KnowledgeBaseController.save"""
    from sqlalchemy import text
    dataset_id = str(uuid.uuid4())
    now = datetime.now()
    db.execute(
        text("""
            INSERT INTO ai_rag_knowledge_dataset (id, dataset_id, name, description, creator, created_at)
            VALUES (:id, :dataset_id, :name, :description, :creator, :created_at)
        """),
        {"id": str(uuid.uuid4()), "dataset_id": dataset_id, "name": body.get("name"), 
         "description": body.get("description", ""), "creator": current_user.id, "created_at": now}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": {"datasetId": dataset_id}}


# ========================================
# 更新知识库
# Migrated from Java: KnowledgeBaseController.update @ PUT /datasets/{dataset_id}
# ========================================
@router.put("/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新知识库 对应Java KnowledgeBaseController.update"""
    from sqlalchemy import text
    existing = db.execute(text("SELECT * FROM ai_rag_knowledge_dataset WHERE dataset_id = :id"), {"id": dataset_id}).first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    existing_dict = dict(existing._mapping)
    if existing_dict.get("creator") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限修改该知识库")
    db.execute(
        text("UPDATE ai_rag_knowledge_dataset SET name = :name, description = :description WHERE dataset_id = :dataset_id"),
        {"name": body.get("name"), "description": body.get("description"), "dataset_id": dataset_id}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 删除知识库
# Migrated from Java: KnowledgeBaseController.delete @ DELETE /datasets/{dataset_id}
# ========================================
@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除知识库 对应Java KnowledgeBaseController.delete"""
    from sqlalchemy import text
    existing = db.execute(text("SELECT * FROM ai_rag_knowledge_dataset WHERE dataset_id = :id"), {"id": dataset_id}).first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    existing_dict = dict(existing._mapping)
    if existing_dict.get("creator") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限删除该知识库")
    db.execute(text("DELETE FROM ai_rag_knowledge_dataset WHERE dataset_id = :id"), {"id": dataset_id})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 批量删除知识库
# Migrated from Java: KnowledgeBaseController.deleteBatch @ DELETE /datasets/batch
# ========================================
@router.delete("/batch")
async def delete_datasets_batch(
    ids: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量删除知识库 对应Java KnowledgeBaseController.deleteBatch"""
    from sqlalchemy import text
    id_list = ids.split(",")
    for ds_id in id_list:
        existing = db.execute(text("SELECT * FROM ai_rag_knowledge_dataset WHERE dataset_id = :id"), {"id": ds_id}).first()
        if existing:
            existing_dict = dict(existing._mapping)
            if existing_dict.get("creator") == current_user.id:
                db.execute(text("DELETE FROM ai_rag_knowledge_dataset WHERE dataset_id = :id"), {"id": ds_id})
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 获取RAG模型列表
# Migrated from Java: KnowledgeBaseController.getRAGModels @ GET /datasets/rag-models
# ========================================
@router.get("/rag-models")
async def get_rag_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取RAG模型列表 对应Java KnowledgeBaseController.getRAGModels"""
    from sqlalchemy import text
    result = db.execute(text("SELECT id, model_name, model_type FROM ai_model_config WHERE model_type = 'rag'")).fetchall()
    models = [dict(row._mapping) for row in result]
    return {"code": 0, "msg": "success", "data": models}