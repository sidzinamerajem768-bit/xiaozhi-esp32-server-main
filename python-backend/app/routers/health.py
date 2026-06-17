"""
健康检查路由
对应Java的OTAController.java的GET /ota/健康检查接口

提供简单的健康检查接口，用于验证服务是否正常运行
"""

from fastapi import APIRouter


# 创建路由器
# 对应Java的@RestController
router = APIRouter(
    prefix="/health",
    tags=["健康检查"],
)


@router.get("")
async def health_check():
    """
    健康检查接口
    
    对应Java的OTAController.java:
        @GetMapping
        public ResponseEntity<String> getOTA() {
            return ResponseEntity.ok("OTA接口运行正常");
        }
    
    返回:
        {"ok": true} - 服务正常
    """
    return {"ok": True}