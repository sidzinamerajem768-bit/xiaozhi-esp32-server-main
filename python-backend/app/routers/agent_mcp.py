"""
MCP接入点管理路由模块
对应Java的AgentMcpAccessPointController.java
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, exc as sa_exc
from app.database import get_db
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/agent/mcp", tags=["MCP接入点管理"])


@router.get("/address/{agentId}")
async def get_mcp_address(agentId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT mcp_url FROM ai_agent_mcp_access_point WHERE agent_id = :aid LIMIT 1"), {"aid": agentId}).first()
        return {"code": 0, "msg": "success", "data": result[0] if result else None}
    except sa_exc.ProgrammingError:
        db.rollback()
        return {"code": 0, "msg": "MCP表不存在", "data": None}


@router.get("/tools/{agentId}")
async def get_mcp_tools(agentId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT tool_name FROM ai_agent_mcp_tools WHERE agent_id = :aid"), {"aid": agentId}).fetchall()
        return {"code": 0, "msg": "success", "data": [r[0] for r in result]}
    except sa_exc.ProgrammingError:
        db.rollback()
        return {"code": 0, "msg": "success", "data": []}