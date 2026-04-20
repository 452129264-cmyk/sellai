"""
全品类商业数据分析系统主服务入口
提供完整的API接口和系统管理功能
"""

import logging
import sys
import time
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .services.industry_service import IndustryAnalysisService
from .services.profit_service import ProfitCalculationService
from .services.trend_service import TrendAnalysisService
from .models.data_models import (
    ProfitAnalysisRequest, ProfitAnalysisResult,
    TrendAnalysisRequest, TrendAnalysisResult,
    IndustryCategory, IndustryProfile,
    SystemConfig
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/business_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="全品类商业数据分析系统",
    description="基于SellAI架构的行业趋势分析、利润测算、风口研判完整决策支持系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务实例
industry_service = None
profit_service = None
trend_service = None


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str
    components: Dict[str, str]


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    service_status: str
    total_industries: int
    total_profiles: int
    trend_accuracy_target: float
    last_updated: str
    components: Dict[str, str]


class ProfitAnalysisResponse(BaseModel):
    """利润分析响应"""
    success: bool
    result: Optional[ProfitAnalysisResult] = None
    error: Optional[str] = None
    processing_time_ms: float


class TrendAnalysisResponse(BaseModel):
    """趋势分析响应"""
    success: bool
    result: Optional[TrendAnalysisResult] = None
    error: Optional[str] = None
    processing_time_ms: float


class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    profit_requests: List[ProfitAnalysisRequest] = []
    trend_requests: List[TrendAnalysisRequest] = []
    notify_completion: bool = False


class BatchAnalysisResponse(BaseModel):
    """批量分析响应"""
    success: bool
    profit_results: List[ProfitAnalysisResult] = []
    trend_results: List[TrendAnalysisResult] = []
    total_analyses: int
    processing_time_ms: float


def initialize_services():
    """初始化服务"""
    global industry_service, profit_service, trend_service
    
    logger.info("正在初始化商业数据分析服务...")
    
    try:
        industry_service = IndustryAnalysisService()
        profit_service = ProfitCalculationService()
        trend_service = TrendAnalysisService()
        
        logger.info("服务初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("启动全品类商业数据分析系统...")
    
    # 确保日志目录存在
    import os
    os.makedirs("logs", exist_ok=True)
    
    # 初始化服务
    if not initialize_services():
        logger.error("服务初始化失败，应用启动中止")
        sys.exit(1)


@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {
        "service": "全品类商业数据分析系统",
        "version": "1.0.0",
        "description": "基于SellAI架构的行业趋势分析、利润测算、风口研判完整决策支持系统",
        "endpoints": [
            "/docs - API文档",
            "/health - 健康检查",
            "/status - 系统状态",
            "/api/v1/profit - 利润分析",
            "/api/v1/trend - 趋势分析",
            "/api/v1/batch - 批量分析"
        ]
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["系统"])
async def health_check():
    """健康检查"""
    services_healthy = all([
        industry_service is not None,
        profit_service is not None,
        trend_service is not None
    ])
    
    status = "healthy" if services_healthy else "unhealthy"
    
    return HealthCheckResponse(
        status=status,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        version="1.0.0",
        components={
            "industry_service": "active" if industry_service else "inactive",
            "profit_service": "active" if profit_service else "inactive",
            "trend_service": "active" if trend_service else "inactive"
        }
    )


@app.get("/status", response_model=SystemStatusResponse, tags=["系统"])
async def system_status():
    """系统状态"""
    if not industry_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        status = industry_service.get_system_status()
        return SystemStatusResponse(**status)
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")


@app.get("/api/v1/industries", tags=["行业分析"])
async def get_industries():
    """获取行业分类"""
    if not industry_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        categories = industry_service.get_industry_categories()
        return {
            "success": True,
            "data": [cat.dict() for cat in categories],
            "total": len(categories)
        }
    except Exception as e:
        logger.error(f"获取行业分类失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行业分类失败: {str(e)}")


@app.get("/api/v1/industries/{industry_id}", tags=["行业分析"])
async def get_industry_profile(industry_id: str):
    """获取行业画像"""
    if not industry_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        profile = industry_service.get_industry_profile(industry_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"行业 {industry_id} 不存在")
        
        return {
            "success": True,
            "data": profile.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行业画像失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行业画像失败: {str(e)}")


@app.post("/api/v1/profit", response_model=ProfitAnalysisResponse, tags=["利润分析"])
async def analyze_profit(request: ProfitAnalysisRequest, background_tasks: BackgroundTasks):
    """利润分析"""
    if not profit_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    start_time = time.time()
    
    try:
        logger.info(f"开始利润分析: 行业={request.industry_id}, 产品={request.product_type}")
        
        # 执行分析
        result = profit_service.analyze_profit(request)
        
        # 计算处理时间
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"利润分析完成: 净利率={result.net_margin:.1f}%, 处理时间={processing_time_ms:.0f}ms")
        
        return ProfitAnalysisResponse(
            success=True,
            result=result,
            processing_time_ms=round(processing_time_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"利润分析失败: {e}")
        processing_time_ms = (time.time() - start_time) * 1000
        
        return ProfitAnalysisResponse(
            success=False,
            error=str(e),
            processing_time_ms=round(processing_time_ms, 2)
        )


@app.post("/api/v1/trend", response_model=TrendAnalysisResponse, tags=["趋势分析"])
async def analyze_trend(request: TrendAnalysisRequest, background_tasks: BackgroundTasks):
    """趋势分析"""
    if not trend_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    start_time = time.time()
    
    try:
        logger.info(f"开始趋势分析: 行业={request.industry_ids}, 时间范围={request.timeframe}")
        
        # 执行分析
        result = trend_service.analyze_market_trends(
            industry_ids=request.industry_ids,
            timeframe=request.timeframe
        )
        
        # 计算处理时间
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"趋势分析完成: 分析{len(request.industry_ids)}个行业, 处理时间={processing_time_ms:.0f}ms")
        
        return TrendAnalysisResponse(
            success=True,
            result=result,
            processing_time_ms=round(processing_time_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"趋势分析失败: {e}")
        processing_time_ms = (time.time() - start_time) * 1000
        
        return TrendAnalysisResponse(
            success=False,
            error=str(e),
            processing_time_ms=round(processing_time_ms, 2)
        )


@app.post("/api/v1/batch", response_model=BatchAnalysisResponse, tags=["批量分析"])
async def batch_analysis(request: BatchAnalysisRequest, background_tasks: BackgroundTasks):
    """批量分析"""
    if not profit_service or not trend_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    start_time = time.time()
    
    try:
        logger.info(f"开始批量分析: {len(request.profit_requests)}个利润分析, {len(request.trend_requests)}个趋势分析")
        
        # 执行利润分析
        profit_results = []
        if request.profit_requests:
            profit_results = profit_service.batch_analyze_profits(request.profit_requests)
        
        # 执行趋势分析
        trend_results = []
        if request.trend_requests:
            trend_results = []
            for trend_request in request.trend_requests:
                try:
                    result = trend_service.analyze_market_trends(
                        industry_ids=trend_request.industry_ids,
                        timeframe=trend_request.timeframe
                    )
                    trend_results.append(result)
                except Exception as e:
                    logger.error(f"批量趋势分析失败: {e}")
                    # 创建错误结果
                    error_result = TrendAnalysisResult(
                        request=trend_request,
                        growth_trends={},
                        momentum_scores={},
                        volatility_scores={},
                        emerging_trends=[],
                        risk_warnings=[],
                        early_signals=[],
                        forecasts={},
                        analysis_timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                        data_coverage={}
                    )
                    trend_results.append(error_result)
        
        # 计算处理时间
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"批量分析完成: 总计{len(profit_results) + len(trend_results)}个分析, 处理时间={processing_time_ms:.0f}ms")
        
        return BatchAnalysisResponse(
            success=True,
            profit_results=profit_results,
            trend_results=trend_results,
            total_analyses=len(profit_results) + len(trend_results),
            processing_time_ms=round(processing_time_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        processing_time_ms = (time.time() - start_time) * 1000
        
        return BatchAnalysisResponse(
            success=False,
            profit_results=[],
            trend_results=[],
            total_analyses=0,
            processing_time_ms=round(processing_time_ms, 2)
        )


@app.get("/api/v1/opportunities", tags=["机会识别"])
async def get_hot_opportunities(min_confidence: float = 0.7, limit: int = 20):
    """获取热门机会"""
    if not trend_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        # 获取所有行业
        industries = industry_service.get_industry_categories()
        industry_ids = [ind.id for ind in industries]
        
        # 识别热门机会
        opportunities = trend_service.identify_hot_opportunities(
            industry_ids=industry_ids,
            min_confidence=min_confidence
        )
        
        # 限制返回数量
        opportunities = opportunities[:limit]
        
        return {
            "success": True,
            "data": opportunities,
            "total": len(opportunities),
            "min_confidence": min_confidence
        }
    except Exception as e:
        logger.error(f"获取热门机会失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取热门机会失败: {str(e)}")


@app.get("/api/v1/benchmarks/{industry_id}", tags=["行业基准"])
async def get_industry_benchmark(industry_id: str):
    """获取行业基准数据"""
    if not industry_service or not profit_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        # 获取行业基准
        profit_benchmark = profit_service.get_profit_benchmark(industry_id)
        
        if not profit_benchmark:
            raise HTTPException(status_code=404, detail=f"行业 {industry_id} 基准数据不存在")
        
        return {
            "success": True,
            "data": profit_benchmark
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行业基准失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行业基准失败: {str(e)}")


@app.get("/api/v1/reports/trend", tags=["报告生成"])
async def generate_trend_report(period: str = "1y", limit_industries: Optional[int] = None):
    """生成趋势报告"""
    if not trend_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        # 获取行业列表（可能限制数量）
        industries = industry_service.get_industry_categories()
        industry_ids = [ind.id for ind in industries]
        
        if limit_industries and limit_industries < len(industry_ids):
            industry_ids = industry_ids[:limit_industries]
        
        # 生成报告
        report = trend_service.generate_trend_report(
            industry_ids=industry_ids,
            report_period=period
        )
        
        return {
            "success": True,
            "data": report,
            "industries_analyzed": len(industry_ids),
            "period": period
        }
    except Exception as e:
        logger.error(f"生成趋势报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成趋势报告失败: {str(e)}")


@app.get("/api/v1/reports/profit", tags=["报告生成"])
async def generate_profit_report(requests: List[ProfitAnalysisRequest]):
    """生成利润报告"""
    if not profit_service:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        # 执行批量分析
        results = profit_service.batch_analyze_profits(requests)
        
        # 生成报告
        report = profit_service.generate_profit_report(results)
        
        return {
            "success": True,
            "data": report,
            "total_analyses": len(results)
        }
    except Exception as e:
        logger.error(f"生成利润报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成利润报告失败: {str(e)}")


def main():
    """主函数"""
    try:
        # 创建配置
        config = SystemConfig()
        
        # 启动服务
        logger.info(f"启动商业数据分析服务，端口: {config.port}")
        
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
            reload=False
        )
        
    except KeyboardInterrupt:
        logger.info("服务被用户中断")
    except Exception as e:
        logger.error(f"服务运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()