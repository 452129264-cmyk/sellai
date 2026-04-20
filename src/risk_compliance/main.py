"""
智能风控合规系统主入口点
启动合规检查服务并提供API接口
"""

import asyncio
import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional

from .database.models import (
    ComplianceRequest,
    ComplianceResult,
    ComplianceConfig,
    ContentType
)
from .services.compliance_service import ComplianceCheckService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局服务实例
compliance_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - 启动时：初始化服务
    - 关闭时：清理资源
    """
    global compliance_service
    
    # 启动时
    logger.info("启动智能风控合规系统...")
    
    try:
        # 加载配置
        config = ComplianceConfig()
        
        # 初始化合规检查服务
        compliance_service = ComplianceCheckService(config)
        
        # 初始化集成服务（需要外部配置）
        # 在实际系统中，这些配置应该从环境变量或配置文件中加载
        notebooklm_config = {
            "api_key": "your_notebooklm_api_key",
            "default_collection": "compliance_knowledge",
            "cache_enabled": True
        }
        
        deepl_config = {
            "api_key": "your_deepl_api_key",
            "plan_type": "pro",
            "cache_enabled": True
        }
        
        originality_config = {
            "service_endpoint": "http://originality-service:8000",
            "api_key": "your_originality_api_key",
            "cache_enabled": True
        }
        
        compliance_service.initialize_integrations(
            notebooklm_config=notebooklm_config,
            deepl_config=deepl_config,
            originality_config=originality_config
        )
        
        logger.info("合规检查服务初始化完成")
        
        yield
        
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        raise
    
    finally:
        # 关闭时
        logger.info("关闭合规检查服务...")
        # 这里可以添加资源清理逻辑

# 创建FastAPI应用
app = FastAPI(
    title="智能风控合规系统API",
    description="基于SellAI架构的全球全行业合规筛查系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依赖函数：获取全局服务实例
def get_compliance_service() -> ComplianceCheckService:
    if compliance_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    return compliance_service

@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "智能风控合规系统",
        "version": "1.0.0",
        "status": "运行中",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "check": "/check",
            "batch-check": "/batch-check"
        }
    }

@app.get("/health")
async def health_check(service: ComplianceCheckService = Depends(get_compliance_service)):
    """健康检查端点"""
    try:
        health_status = await service.check_health()
        return health_status
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"健康检查失败: {str(e)}")

@app.get("/status")
async def get_status(service: ComplianceCheckService = Depends(get_compliance_service)):
    """获取服务状态"""
    try:
        status = await service.get_service_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@app.post("/check", response_model=ComplianceResult)
async def check_content(
    request: ComplianceRequest,
    service: ComplianceCheckService = Depends(get_compliance_service)
):
    """
    单内容合规检查
    - content_id: 内容唯一标识
    - text: 待检查文本
    - content_type: 内容类型 (advertisement, product, social, email, web, document)
    - target_country: 目标国家代码 (US, CN, EU, JP等)
    - industry: 行业分类 (可选)
    - context: 上下文信息 (可选)
    """
    try:
        logger.info(f"收到合规检查请求: content_id={request.content_id}, "
                   f"country={request.target_country}, type={request.content_type}")
        
        result = await service.check_content(request)
        
        logger.info(f"合规检查完成: content_id={request.content_id}, "
                   f"risk_level={result.risk_level}, score={result.risk_score:.2f}")
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"合规检查异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.post("/batch-check")
async def batch_check_content(
    requests: List[ComplianceRequest],
    service: ComplianceCheckService = Depends(get_compliance_service)
):
    """
    批量内容合规检查
    - 最多支持100个请求
    """
    # 限制批量请求数量
    if len(requests) > 100:
        raise HTTPException(status_code=400, detail="批量请求数量超过限制 (最多100个)")
    
    try:
        logger.info(f"收到批量合规检查请求: count={len(requests)}")
        
        results = await service.batch_check_content(requests)
        
        logger.info(f"批量合规检查完成: count={len(results)}")
        
        return {
            "success": True,
            "total_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"批量合规检查异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/supported-countries")
async def get_supported_countries():
    """获取支持的国家列表"""
    # 从配置中获取
    config = ComplianceConfig()
    
    return {
        "supported_countries": config.supported_countries,
        "total_count": len(config.supported_countries)
    }

@app.get("/content-types")
async def get_content_types():
    """获取支持的内容类型"""
    content_types = [
        {"value": ct.value, "description": ct.name.replace("_", " ").title()}
        for ct in ContentType
    ]
    
    return {
        "content_types": content_types,
        "total_count": len(content_types)
    }

@app.post("/config/update")
async def update_config(
    config_data: dict,
    service: ComplianceCheckService = Depends(get_compliance_service)
):
    """更新服务配置"""
    try:
        service.update_config(config_data)
        
        return {
            "success": True,
            "message": "配置更新成功"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")

@app.post("/stats/reset")
async def reset_stats(
    service: ComplianceCheckService = Depends(get_compliance_service)
):
    """重置统计信息"""
    try:
        service.reset_service_stats()
        
        return {
            "success": True,
            "message": "统计信息已重置"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置统计失败: {str(e)}")

if __name__ == "__main__":
    # 启动FastAPI服务器
    uvicorn.run(
        "src.risk_compliance.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下自动重载
        log_level="info"
    )