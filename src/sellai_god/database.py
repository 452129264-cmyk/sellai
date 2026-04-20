"""
封神版数据库层 — 使用内置 sqlite3，零额外依赖
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join("data", "sellai_god.db")

def _get_conn() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

@contextmanager
def db_ctx():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """建表（幂等）"""
    with db_ctx() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS god_users (
                id          TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                email       TEXT UNIQUE,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS god_ai_avatars (
                id           TEXT PRIMARY KEY,
                user_id      TEXT NOT NULL,
                name         TEXT NOT NULL,
                personality  TEXT,
                status       TEXT NOT NULL DEFAULT 'idle',
                avatar_url   TEXT,
                unread_count INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES god_users(id)
            );

            CREATE TABLE IF NOT EXISTS god_tasks (
                id           TEXT PRIMARY KEY,
                avatar_id    TEXT NOT NULL,
                title        TEXT NOT NULL,
                description  TEXT,
                status       TEXT NOT NULL DEFAULT 'pending',
                priority     INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (avatar_id) REFERENCES god_ai_avatars(id)
            );

            CREATE TABLE IF NOT EXISTS god_opportunities (
                id           TEXT PRIMARY KEY,
                title        TEXT NOT NULL,
                description  TEXT,
                source       TEXT,
                platform     TEXT,
                revenue      REAL DEFAULT 0.0,
                cost         REAL DEFAULT 0.0,
                gross_margin REAL DEFAULT 0.0,
                category     TEXT,
                status       TEXT DEFAULT 'active',
                url          TEXT,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS god_chat_messages (
                id         TEXT PRIMARY KEY,
                avatar_id  TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (avatar_id) REFERENCES god_ai_avatars(id)
            );

            -- ── 社交关系表 ─────────────────────────────────────────
            -- 两个分身之间的连接记录（status: pending | accepted | rejected）
            CREATE TABLE IF NOT EXISTS god_social_connections (
                id         TEXT PRIMARY KEY,
                from_id    TEXT NOT NULL,
                to_id      TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'accepted',
                message    TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(from_id, to_id),
                FOREIGN KEY (from_id) REFERENCES god_ai_avatars(id),
                FOREIGN KEY (to_id)   REFERENCES god_ai_avatars(id)
            );

            -- 分身间社交消息（区别于 god_chat_messages 的用户↔分身对话）
            CREATE TABLE IF NOT EXISTS god_social_messages (
                id         TEXT PRIMARY KEY,
                from_id    TEXT NOT NULL,
                to_id      TEXT NOT NULL,
                content    TEXT NOT NULL,
                is_read    INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (from_id) REFERENCES god_ai_avatars(id),
                FOREIGN KEY (to_id)   REFERENCES god_ai_avatars(id)
            );

            -- 默认用户（无需登录 MVP）
            INSERT OR IGNORE INTO god_users (id, username, email, created_at)
            VALUES ('default_user', 'Admin', 'admin@sellai.com', datetime('now'));
        """)
