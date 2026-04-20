"""
封神版 — SellAI 主对话入口
POST /api/main/chat  多轮对话 + 全自动执行 + 主动追问
"""
import json
import os
import re
from datetime import datetime
from typing import Optional
from uuid import uuid4

import requests
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .database import db_ctx

router = APIRouter()

# ── 系统提示词 ────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """你是 SellAI，一个主动的电商 AI 合伙人。你的工作方式：

1. 主动收集信息：当用户需求不完整时，用简短的问题追问缺失信息（商品类型、目标毛利、预算、平台等），每次只问一个问题。
2. 全自动执行：信息收集完整后，立刻宣布要执行的操作，不需要用户再点按钮。
3. 意图识别：分析对话历史，判断当前是否已具备执行条件。

回复格式（严格 JSON，禁止加 markdown 代码块）：
{
  "reply": "对用户说的话（自然语言，100字以内）",
  "need_more_info": true/false,
  "execute": {
    "action": "find_product" | "create_avatar" | "none",
    "keywords": ["关键词1"],
    "margin_threshold": 数字（毛利%，默认30）,
    "avatar_type": "分身类型名称或null"
  }
}

示例1 — 信息不足，继续追问：
用户说"我想卖女装" →
{"reply":"好的！您想主攻哪个细分品类？连衣裙 / 上衣 / 裤子 / 外套？","need_more_info":true,"execute":{"action":"none","keywords":[],"margin_threshold":30,"avatar_type":null}}

示例2 — 信息完整，立刻执行：
用户说"连衣裙，毛利50%" →
{"reply":"收到！正在为您创建商务分身，搜索毛利≥50%的连衣裙商机...","need_more_info":false,"execute":{"action":"find_product","keywords":["连衣裙"],"margin_threshold":50,"avatar_type":"女装销售分身"}}

示例3 — 直接找商品：
用户说"帮我找毛利50%的商品" →
{"reply":"好的，马上为您扫描毛利≥50%的商机并创建分身跟进！","need_more_info":false,"execute":{"action":"find_product","keywords":[],"margin_threshold":50,"avatar_type":"商机分析分身"}}
"""


# ── Pydantic 模型 ─────────────────────────────────────────────────────────────

class MainChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    user_id: str = "default_user"
    session_id: Optional[str] = None


# ── 会话历史 ──────────────────────────────────────────────────────────────────

def _load_history(session_id: str, limit: int = 10) -> list[dict]:
    """从 DB 加载最近 N 轮对话（god_chat_messages 以 session_id 作 avatar_id）"""
    with db_ctx() as conn:
        rows = conn.execute(
            "SELECT role, content FROM god_chat_messages "
            "WHERE avatar_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _save_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """保存一轮对话到 DB"""
    now = datetime.utcnow().isoformat()
    with db_ctx() as conn:
        conn.execute(
            "INSERT INTO god_chat_messages (id,avatar_id,role,content,created_at) VALUES (?,?,?,?,?)",
            (str(uuid4()), session_id, "user", user_msg, now)
        )
        conn.execute(
            "INSERT INTO god_chat_messages (id,avatar_id,role,content,created_at) VALUES (?,?,?,?,?)",
            (str(uuid4()), session_id, "assistant", assistant_msg, now)
        )


# ── AI 调用 ───────────────────────────────────────────────────────────────────

def _call_qwen(messages: list[dict]) -> str:
    """多轮调用千问，返回原始文本"""
    api_key = os.environ.get("BAILIAN_API_KEY", "")
    if api_key:
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model = "qwen-turbo"
    else:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key:
        return ""

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": _SYSTEM_PROMPT}] + messages,
                "max_tokens": 600,
                "temperature": 0.6,
            },
            timeout=25.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def _parse_ai_response(raw: str) -> dict:
    """从 AI 原始输出中提取 JSON，失败时返回安全默认值"""
    try:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {
        "reply": raw or "我是 SellAI，请告诉我您的电商需求！",
        "need_more_info": True,
        "execute": {"action": "none", "keywords": [], "margin_threshold": 30, "avatar_type": None},
    }


# ── 自动执行动作 ──────────────────────────────────────────────────────────────

def _auto_create_avatar(user_id: str, avatar_type: str) -> dict:
    avatar_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    name = avatar_type or "智能分身"
    with db_ctx() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO god_users (id,username,email,created_at) VALUES (?,?,?,?)",
            (user_id, user_id, None, now)
        )
        conn.execute(
            "INSERT INTO god_ai_avatars "
            "(id,user_id,name,personality,status,avatar_url,unread_count,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (avatar_id, user_id, name, name, "idle", None, 0, now)
        )
    return {"id": avatar_id, "name": name}


def _find_opportunities(keywords: list, margin_threshold: float) -> list:
    from .opportunity_engine import seed_opportunities_to_db
    with db_ctx() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM god_opportunities WHERE status='active'"
        ).fetchone()[0]
        if count == 0:
            seed_opportunities_to_db(conn)

        kw_filter = ""
        params: list = [margin_threshold]
        if keywords:
            clauses = " OR ".join(["title LIKE ?" for _ in keywords])
            kw_filter = f" AND ({clauses})"
            params += [f"%{k}%" for k in keywords]

        sql = (
            "SELECT * FROM god_opportunities "
            f"WHERE status='active' AND gross_margin >= ?{kw_filter} "
            "ORDER BY gross_margin DESC LIMIT 5"
        )
        rows = conn.execute(sql, params).fetchall()

    # 若关键词过滤后为空，退回不带关键词的结果
    if not rows and keywords:
        with db_ctx() as conn:
            rows = conn.execute(
                "SELECT * FROM god_opportunities WHERE status='active' AND gross_margin >= ? "
                "ORDER BY gross_margin DESC LIMIT 5",
                (margin_threshold,)
            ).fetchall()

    return [dict(r) for r in rows]


# ── 主路由 ────────────────────────────────────────────────────────────────────

@router.post("/main/chat", summary="SellAI 主对话：多轮追问 + 全自动执行")
async def main_chat(body: MainChatRequest):
    session_id = body.session_id or f"main_{body.user_id}"

    # 1. 加载历史，构造多轮消息
    history = _load_history(session_id)
    messages = history + [{"role": "user", "content": body.content}]

    # 2. 调用 AI（一次调用同时完成意图判断 + 追问 + 回复生成）
    raw = _call_qwen(messages)
    parsed = _parse_ai_response(raw)

    reply_text = parsed.get("reply", "")
    exec_info = parsed.get("execute", {})
    action = exec_info.get("action", "none")
    margin_threshold = float(exec_info.get("margin_threshold", 30))
    keywords = exec_info.get("keywords", [])
    avatar_type = exec_info.get("avatar_type")

    # 3. 根据 AI 决策执行自动化动作
    actions_taken = []
    avatar_created = None
    opportunities = []

    if action == "find_product":
        opportunities = _find_opportunities(keywords, margin_threshold)
        avatar_created = _auto_create_avatar(body.user_id, avatar_type or "商机分析分身")
        actions_taken.append(f"扫描商机库，找到 {len(opportunities)} 个毛利≥{margin_threshold:.0f}% 的商品")
        actions_taken.append(f"自动创建分身「{avatar_created['name']}」跟进任务")

    elif action == "create_avatar":
        avatar_created = _auto_create_avatar(body.user_id, avatar_type or "智能分身")
        actions_taken.append(f"已创建分身「{avatar_created['name']}」")

    # 4. AI 未能给出 reply 时的降级文本
    if not reply_text:
        if action == "find_product":
            reply_text = (
                f"已为您扫描商机！找到 {len(opportunities)} 个毛利≥{margin_threshold:.0f}% 的商品，"
                f"并自动创建「{avatar_created['name']}」跟进。"
            )
        elif action == "create_avatar":
            reply_text = f"已为您创建分身「{avatar_created['name']}」，它将自动执行相关任务。"
        else:
            reply_text = "我是 SellAI 电商助手，请告诉我您想卖什么、目标毛利是多少？"

    # 5. 持久化本轮对话
    _save_turn(session_id, body.content, reply_text)

    return {
        "success": True,
        "reply": reply_text,
        "need_more_info": parsed.get("need_more_info", True),
        "intent": action,
        "actions_taken": actions_taken,
        "avatar_created": avatar_created,
        "opportunities": opportunities[:3],
        "timestamp": datetime.utcnow().isoformat(),
    }
