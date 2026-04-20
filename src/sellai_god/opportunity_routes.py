"""
封神版 — 商机 API 路由
端点：
  GET  /api/opportunities          获取商机列表（严格毛利 ≥ 30%）
  POST /api/opportunities/refresh  手动刷新商机（重新爬取+入库）
"""
from datetime import datetime
from fastapi import APIRouter, Query

from .database import db_ctx
from .opportunity_engine import fetch_opportunities, seed_opportunities_to_db, MARGIN_THRESHOLD

router = APIRouter()


@router.get("/opportunities", summary="获取商机列表（毛利 ≥ 30%）")
async def list_opportunities(
    limit: int = Query(default=20, ge=1, le=100),
    category: str = Query(default=None),
    platform: str = Query(default=None),
    min_margin: float = Query(default=30.0, ge=0.0, le=100.0),
):
    """
    严格返回毛利率 ≥ min_margin（默认30%）的商机。
    优先从数据库读取；若库为空则实时生成。
    """
    with db_ctx() as conn:
        # 检查数据库是否有数据
        count = conn.execute(
            "SELECT COUNT(*) FROM god_opportunities WHERE status='active'"
        ).fetchone()[0]

        if count == 0:
            # 首次或库为空：写入种子数据
            seed_opportunities_to_db(conn)

        # 构建查询
        sql = "SELECT * FROM god_opportunities WHERE status='active' AND gross_margin >= ?"
        params: list = [min_margin]
        if category:
            sql += " AND category=?"
            params.append(category)
        if platform:
            sql += " AND platform=?"
            params.append(platform)
        sql += " ORDER BY gross_margin DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()

    opportunities = [dict(r) for r in rows]
    return {
        "success": True,
        "total": len(opportunities),
        "margin_threshold": min_margin,
        "fetched_at": datetime.utcnow().isoformat(),
        "opportunities": opportunities
    }


@router.post("/opportunities/refresh", summary="手动刷新商机数据库")
async def refresh_opportunities():
    """重新爬取/生成商机数据并写入数据库"""
    with db_ctx() as conn:
        count = seed_opportunities_to_db(conn)
    return {
        "success": True,
        "seeded": count,
        "margin_threshold": MARGIN_THRESHOLD * 100,
        "refreshed_at": datetime.utcnow().isoformat()
    }
