"""
自动执行链路：商机爬取 → 写库 → 创建分身 → 分配任务 → 推送通知
每 30 分钟由后台线程触发一次，不阻塞主服务。
"""
import threading
import logging
import time
from datetime import datetime
from uuid import uuid4

from .database import db_ctx
from .opportunity_engine import fetch_opportunities

logger = logging.getLogger(__name__)

# 品类 → 分身角色映射
_CATEGORY_ROLE = {
    "数码配件": "数码选品专员",
    "美妆护肤": "美妆运营专员",
    "家居日用": "家居选品专员",
    "运动健身": "运动健康专员",
    "食品":     "食品供应链专员",
    "母婴":     "母婴用品专员",
    "宠物用品": "宠物市场专员",
    "跨境电商": "跨境选品专员",
}

INTERVAL_SECONDS = 1800  # 30 分钟


def _run_once() -> dict:
    """执行一次完整链路，返回本次执行摘要。"""
    summary = {"opportunities": 0, "avatars_created": 0, "tasks_created": 0, "errors": []}
    try:
        # 1. 爬取 / 生成商机
        opps = fetch_opportunities(limit=50)
        summary["opportunities"] = len(opps)

        with db_ctx() as conn:
            # 2. 写入商机库（清空旧 active 记录）
            conn.execute("DELETE FROM god_opportunities WHERE status='active'")
            for o in opps:
                conn.execute("""
                    INSERT OR REPLACE INTO god_opportunities
                    (id, title, description, source, platform, revenue, cost,
                     gross_margin, category, status, url, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    o["id"], o["title"], o["description"], o["source"],
                    o["platform"], o["revenue"], o["cost"], o["gross_margin"],
                    o["category"], "active", o["url"], o["created_at"],
                ))

            # 3. 按品类汇总，每个新品类创建一个专属分身
            categories = {o["category"] for o in opps}
            for cat in categories:
                role = _CATEGORY_ROLE.get(cat, f"{cat}专员")
                # 检查是否已有同名分身
                row = conn.execute(
                    "SELECT id FROM god_ai_avatars WHERE name=?", (role,)
                ).fetchone()
                if row:
                    avatar_id = row["id"]
                else:
                    avatar_id = str(uuid4())
                    conn.execute("""
                        INSERT INTO god_ai_avatars
                        (id, user_id, name, personality, status, created_at)
                        VALUES (?,?,?,?,?,?)
                    """, (
                        avatar_id, "default_user", role,
                        f"专注{cat}品类的选品与运营，精通市场趋势与毛利分析",
                        "active", datetime.now().isoformat(),
                    ))
                    summary["avatars_created"] += 1
                    logger.info(f"[AutoChain] 创建分身: {role} ({avatar_id})")

                # 4. 为该分身分配本轮最高毛利商机任务
                top_opp = max(
                    (o for o in opps if o["category"] == cat),
                    key=lambda x: x["gross_margin"],
                )
                task_title = f"跟进商机：{top_opp['title']} (毛利 {top_opp['gross_margin']:.1f}%)"
                # 避免重复创建同名任务
                exists = conn.execute(
                    "SELECT id FROM god_tasks WHERE avatar_id=? AND title=?",
                    (avatar_id, task_title),
                ).fetchone()
                if not exists:
                    conn.execute("""
                        INSERT INTO god_tasks
                        (id, avatar_id, title, description, status, priority, created_at)
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        str(uuid4()), avatar_id, task_title,
                        f"平台: {top_opp['platform']} | 售价: ¥{top_opp['revenue']} | "
                        f"成本: ¥{top_opp['cost']} | 毛利率: {top_opp['gross_margin']:.1f}%",
                        "pending", 1, datetime.now().isoformat(),
                    ))
                    summary["tasks_created"] += 1

        # 5. 推送通知（打印到服务日志，可后续接 webhook）
        _push_notification(summary, opps)

    except Exception as e:
        summary["errors"].append(str(e))
        logger.error(f"[AutoChain] 执行异常: {e}")

    return summary


def _push_notification(summary: dict, opps: list) -> None:
    top5 = sorted(opps, key=lambda x: x["gross_margin"], reverse=True)[:5]
    lines = [
        f"\n{'='*55}",
        f"[SellAI AutoChain] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  商机数量: {summary['opportunities']}  新建分身: {summary['avatars_created']}  新建任务: {summary['tasks_created']}",
        "  Top-5 高毛利商机:",
    ]
    for i, o in enumerate(top5, 1):
        lines.append(f"    {i}. [{o['platform']}] {o['title']} — 毛利 {o['gross_margin']:.1f}%")
    lines.append("=" * 55)
    print("\n".join(lines), flush=True)
    logger.info(f"[AutoChain] 本轮完成: {summary}")


def _background_loop() -> None:
    """后台守护线程，每 INTERVAL_SECONDS 执行一次链路。"""
    logger.info("[AutoChain] 后台链路线程启动")
    # 启动时立即执行一次
    _run_once()
    while True:
        time.sleep(INTERVAL_SECONDS)
        _run_once()


def start_background_chain() -> None:
    """在 FastAPI lifespan 里调用，启动后台链路线程。"""
    t = threading.Thread(target=_background_loop, name="AutoExecutionChain", daemon=True)
    t.start()
    logger.info("[AutoChain] 后台自动执行链路已启动（间隔 30 分钟）")
