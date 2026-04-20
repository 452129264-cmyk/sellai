"""
封神版 — AI 主动社交模块
包含：
  匹配引擎       基于人设标签 + 任务类型的 Jaccard + 互补加成算法
  GET  /api/social/matches      为某分身返回排名推荐列表
  POST /api/social/connect      发起/接受连接
  GET  /api/social/connections  查看某分身的全部连接
  POST /api/social/chat         分身间发送消息（含自动回复）
  GET  /api/social/messages     获取两个分身间的对话记录
"""
import random
import re
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .database import db_ctx

router = APIRouter()

# ─── 标签体系 ──────────────────────────────────────────────────────────────────

_ROLE_TAGS   = {'销售', '运营', '创作', '推广', '分析', '谈判', '客服', '采购', '策划', '主播'}
_DOMAIN_TAGS = {'美妆', '数码', '服装', '食品', '家居', '宠物', '运动', '母婴', '跨境', '教育'}
_STYLE_TAGS  = {'专业', '友善', '高效', '积极', '主动', '创新', '细致', '稳健', '幽默'}
_ALL_TAGS    = _ROLE_TAGS | _DOMAIN_TAGS | _STYLE_TAGS

# 互补角色对：不同但协作效果好
_COMPLEMENT_PAIRS = [
    ({'销售', '推广', '主播'}, {'运营', '分析', '策划'}),
    ({'创作'},                 {'推广', '销售', '主播'}),
    ({'谈判', '采购'},         {'客服', '运营'}),
    ({'策划'},                 {'创作', '运营'}),
]


def _extract_tags(avatar: dict) -> set:
    """从分身的 name + personality 字段提取标签集合"""
    text = ' '.join(filter(None, [
        avatar.get('name', ''),
        avatar.get('personality', '')
    ]))
    return {tag for tag in _ALL_TAGS if tag in text}


def _compute_score(a_tags: set, b_tags: set) -> float:
    """
    综合得分 = Jaccard相似度×0.45 + 互补加成×0.30 + 风格匹配×0.10 + 基础分0.20
    结果范围 [0.20, 0.99]
    """
    base = 0.20

    # Jaccard：共有标签越多越高
    union = a_tags | b_tags
    inter = a_tags & b_tags
    jaccard = len(inter) / len(union) if union else 0

    # 互补加成：不同角色互相补充
    comp = 0.0
    for set_a, set_b in _COMPLEMENT_PAIRS:
        if (a_tags & set_a and b_tags & set_b) or (b_tags & set_a and a_tags & set_b):
            comp = 0.30
            break

    # 风格匹配加成：相同风格标签
    style_shared = (a_tags & _STYLE_TAGS) & (b_tags & _STYLE_TAGS)
    style_bonus = min(len(style_shared) * 0.05, 0.15)

    raw = base + jaccard * 0.45 + comp + style_bonus
    return round(min(raw, 0.99), 2)


def _match_reason(a_tags: set, b_tags: set, score: float) -> str:
    """生成可读的匹配理由"""
    shared = a_tags & b_tags
    comp_roles = set()
    for set_a, set_b in _COMPLEMENT_PAIRS:
        if (a_tags & set_a and b_tags & set_b) or (b_tags & set_a and a_tags & set_b):
            comp_roles = (a_tags & (set_a | set_b)) | (b_tags & (set_a | set_b))
            break

    if score >= 0.80:
        return f"高度匹配！共有标签：{'、'.join(shared) if shared else '综合互补'}，协作潜力极强。"
    elif score >= 0.60:
        shared_str = '、'.join(list(shared)[:3]) if shared else ''
        comp_str   = '、'.join(list(comp_roles)[:3]) if comp_roles else ''
        parts = [p for p in [shared_str and f"共同擅长 {shared_str}", comp_str and f"互补能力 {comp_str}"] if p]
        return '，'.join(parts) + '。' if parts else "多维度匹配，建议合作探索。"
    else:
        return "存在合作可能，可进一步了解。"


# ─── Pydantic 请求模型 ─────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    from_id: str
    to_id:   str
    message: Optional[str] = None

class ChatRequest(BaseModel):
    from_id: str
    to_id:   str
    content: str = Field(..., min_length=1)


# ─── 社交回复生成 ──────────────────────────────────────────────────────────────

def _social_reply(replier: dict, sender_name: str, msg: str) -> str:
    """由 replier 分身自动回复 sender 的消息"""
    name     = replier.get('name', 'AI分身')
    tags     = _extract_tags(replier)
    role_str = '、'.join(list(tags & _ROLE_TAGS)[:2]) or '综合'
    preview  = msg[:28] + ('...' if len(msg) > 28 else '')

    templates = [
        f"你好 {sender_name}！我是 {name}，专注于{role_str}方向。关于「{preview}」，我有一些想法，我们可以深入聊聊！",
        f"{name} 收到！「{preview}」这个方向很有意思，结合我的{role_str}经验，我觉得可以从高毛利品类切入，期待合作。",
        f"感谢联系！{name} 正在分析「{preview}」，初步判断可行性较高，建议我们共同评估一下资源匹配度。",
        f"嗨 {sender_name}！「{preview}」这个点我之前也研究过，{name} 的{role_str}能力可以直接支撑，我们连线深聊吧。",
        f"{name} 已接收你的消息。关于{role_str}合作，我建议先对齐目标品类和毛利预期，再分工协作会更高效。",
    ]
    return random.choice(templates)


# ─── 路由 ─────────────────────────────────────────────────────────────────────

@router.get("/social/matches", summary="获取分身匹配推荐列表")
async def get_matches(avatar_id: str, limit: int = Query(default=10, ge=1, le=50)):
    """
    基于 Jaccard 相似度 + 互补角色加成，为指定分身推荐潜在合作伙伴。
    排除自身，按匹配得分降序返回。
    """
    with db_ctx() as conn:
        self_row = conn.execute(
            "SELECT * FROM god_ai_avatars WHERE id=?", (avatar_id,)
        ).fetchone()
        if not self_row:
            raise HTTPException(status_code=404, detail="分身不存在")

        others = conn.execute(
            "SELECT * FROM god_ai_avatars WHERE id != ?", (avatar_id,)
        ).fetchall()

        # 已有连接的分身集合
        connected_ids = set()
        for row in conn.execute(
            "SELECT from_id, to_id FROM god_social_connections WHERE from_id=? OR to_id=?",
            (avatar_id, avatar_id)
        ).fetchall():
            connected_ids.add(row['from_id'])
            connected_ids.add(row['to_id'])
        connected_ids.discard(avatar_id)

    self_av   = dict(self_row)
    self_tags = _extract_tags(self_av)

    results = []
    for row in others:
        other = dict(row)
        other_tags = _extract_tags(other)
        score      = _compute_score(self_tags, other_tags)
        reason     = _match_reason(self_tags, other_tags, score)
        # 显式标记是否已连接
        other['match_score']    = score
        other['match_reason']   = reason
        other['match_tags']     = list(other_tags)
        other['is_connected']   = other['id'] in connected_ids
        results.append(other)

    results.sort(key=lambda x: x['match_score'], reverse=True)
    return {
        "success":      True,
        "avatar_id":    avatar_id,
        "self_tags":    list(self_tags),
        "matches":      results[:limit],
        "total":        len(results),
    }


@router.post("/social/connect", summary="发起分身间连接")
async def connect_avatars(body: ConnectRequest):
    """创建两个分身间的连接关系（MVP 下自动 accepted）"""
    if body.from_id == body.to_id:
        raise HTTPException(status_code=400, detail="不能连接自身")

    now = datetime.utcnow().isoformat()
    conn_id = str(uuid4())

    with db_ctx() as conn:
        for av_id in (body.from_id, body.to_id):
            av = conn.execute(
                "SELECT id FROM god_ai_avatars WHERE id=?", (av_id,)
            ).fetchone()
            if not av:
                raise HTTPException(status_code=404, detail=f"分身 {av_id} 不存在")

        # 检查是否已连接
        existing = conn.execute(
            """SELECT id FROM god_social_connections
               WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)""",
            (body.from_id, body.to_id, body.to_id, body.from_id)
        ).fetchone()
        if existing:
            return {"success": True, "already_connected": True,
                    "conn_id": existing['id']}

        conn.execute("""
            INSERT INTO god_social_connections
            (id, from_id, to_id, status, message, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?)
        """, (conn_id, body.from_id, body.to_id, 'accepted',
              body.message, now, now))

    return {
        "success":    True,
        "conn_id":    conn_id,
        "from_id":    body.from_id,
        "to_id":      body.to_id,
        "status":     "accepted",
        "created_at": now,
    }


@router.get("/social/connections", summary="获取分身的全部连接")
async def list_connections(avatar_id: str):
    with db_ctx() as conn:
        rows = conn.execute("""
            SELECT c.*,
                   a1.name AS from_name, a1.personality AS from_personality,
                   a2.name AS to_name,   a2.personality AS to_personality
            FROM god_social_connections c
            JOIN god_ai_avatars a1 ON a1.id = c.from_id
            JOIN god_ai_avatars a2 ON a2.id = c.to_id
            WHERE c.from_id=? OR c.to_id=?
            ORDER BY c.created_at DESC
        """, (avatar_id, avatar_id)).fetchall()
    return {"success": True, "connections": [dict(r) for r in rows]}


@router.post("/social/chat", summary="分身间发送消息（含自动回复）")
async def social_chat(body: ChatRequest):
    """
    from_id 分身向 to_id 分身发送消息。
    系统自动以 to_id 分身的身份生成回复，模拟真实的分身间对话。
    """
    now = datetime.utcnow().isoformat()
    with db_ctx() as conn:
        from_av = conn.execute(
            "SELECT * FROM god_ai_avatars WHERE id=?", (body.from_id,)
        ).fetchone()
        to_av = conn.execute(
            "SELECT * FROM god_ai_avatars WHERE id=?", (body.to_id,)
        ).fetchone()
        if not from_av:
            raise HTTPException(status_code=404, detail=f"发送方分身 {body.from_id} 不存在")
        if not to_av:
            raise HTTPException(status_code=404, detail=f"接收方分身 {body.to_id} 不存在")

        # 若未连接，自动建立连接
        existing = conn.execute(
            """SELECT id FROM god_social_connections
               WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)""",
            (body.from_id, body.to_id, body.to_id, body.from_id)
        ).fetchone()
        if not existing:
            conn.execute("""
                INSERT INTO god_social_connections
                (id, from_id, to_id, status, message, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?)
            """, (str(uuid4()), body.from_id, body.to_id, 'accepted', None, now, now))

        # 存储发送方消息
        msg_id = str(uuid4())
        conn.execute("""
            INSERT INTO god_social_messages (id, from_id, to_id, content, is_read, created_at)
            VALUES (?,?,?,?,?,?)
        """, (msg_id, body.from_id, body.to_id, body.content, 0, now))

        # 生成接收方自动回复
        reply_content = _social_reply(dict(to_av), dict(from_av)['name'], body.content)
        reply_id      = str(uuid4())
        reply_time    = datetime.utcnow().isoformat()
        conn.execute("""
            INSERT INTO god_social_messages (id, from_id, to_id, content, is_read, created_at)
            VALUES (?,?,?,?,?,?)
        """, (reply_id, body.to_id, body.from_id, reply_content, 0, reply_time))

        # 更新接收方未读数
        conn.execute(
            "UPDATE god_ai_avatars SET unread_count=unread_count+1 WHERE id=?",
            (body.to_id,)
        )

    return {
        "success": True,
        "sent": {
            "id": msg_id, "from_id": body.from_id, "to_id": body.to_id,
            "content": body.content, "created_at": now
        },
        "reply": {
            "id": reply_id, "from_id": body.to_id, "to_id": body.from_id,
            "content": reply_content, "created_at": reply_time
        }
    }


@router.get("/social/messages", summary="获取两个分身间的对话记录")
async def get_social_messages(
    from_id: str,
    to_id:   str,
    limit:   int = Query(default=50, ge=1, le=200)
):
    """返回 from_id ↔ to_id 之间的全部消息，按时间升序排列"""
    with db_ctx() as conn:
        rows = conn.execute("""
            SELECT m.*, a.name AS sender_name
            FROM god_social_messages m
            JOIN god_ai_avatars a ON a.id = m.from_id
            WHERE (m.from_id=? AND m.to_id=?) OR (m.from_id=? AND m.to_id=?)
            ORDER BY m.created_at ASC
            LIMIT ?
        """, (from_id, to_id, to_id, from_id, limit)).fetchall()

        # 标记已读
        conn.execute("""
            UPDATE god_social_messages SET is_read=1
            WHERE to_id=? AND from_id=? AND is_read=0
        """, (from_id, to_id))

    return {"success": True, "messages": [dict(r) for r in rows]}
