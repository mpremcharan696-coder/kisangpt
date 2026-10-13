"""
chatbot_db.py
=============
SQLite Persistence for 1-to-1 Interactive Voice Chatbot.
Maintains chat sessions, bilingual message turns, and extracted farmer memory
in schemes_dev.db.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "schemes_dev.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_chat_tables() -> None:
    """Create chat tables if they do not exist."""
    conn = get_db()
    cur = conn.cursor()

    # Chat Sessions Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            farmer_name TEXT DEFAULT 'Farmer',
            preferred_language TEXT DEFAULT 'Kannada',
            selected_voice TEXT DEFAULT 'meera',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Chat Messages Table (Stores separate Kannada and English replies in respective columns)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            kannada_reply TEXT,
            english_reply TEXT,
            audio_base64 TEXT,
            intent TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        )
    """)

    # Farmer Memory Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS farmer_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            memory_key TEXT NOT NULL,
            memory_value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, memory_key)
        )
    """)

    conn.commit()
    conn.close()


def create_or_get_session(
    session_id: str,
    farmer_name: str = "Farmer",
    preferred_language: str = "Kannada",
    selected_voice: str = "meera"
) -> Dict[str, Any]:
    """Retrieve existing session or create a new session."""
    init_chat_tables()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()

    if row:
        session = dict(row)
    else:
        cur.execute("""
            INSERT INTO chat_sessions (id, farmer_name, preferred_language, selected_voice)
            VALUES (?, ?, ?, ?)
        """, (session_id, farmer_name, preferred_language, selected_voice))
        conn.commit()
        session = {
            "id": session_id,
            "farmer_name": farmer_name,
            "preferred_language": preferred_language,
            "selected_voice": selected_voice,
        }

    conn.close()
    return session


def update_session(
    session_id: str,
    preferred_language: Optional[str] = None,
    selected_voice: Optional[str] = None,
    farmer_name: Optional[str] = None
) -> None:
    """Update session preferences."""
    conn = get_db()
    cur = conn.cursor()
    updates = []
    params = []

    if preferred_language:
        updates.append("preferred_language = ?")
        params.append(preferred_language)
    if selected_voice:
        updates.append("selected_voice = ?")
        params.append(selected_voice)
    if farmer_name:
        updates.append("farmer_name = ?")
        params.append(farmer_name)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE chat_sessions SET {', '.join(updates)} WHERE id = ?"
        params.append(session_id)
        cur.execute(query, tuple(params))
        conn.commit()

    conn.close()


def save_message_turn(
    session_id: str,
    sender: str,
    kannada_reply: str,
    english_reply: str,
    audio_base64: Optional[str] = None,
    intent: Optional[str] = None
) -> int:
    """Store message turn with respective Kannada and English replies."""
    init_chat_tables()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO chat_messages (session_id, sender, kannada_reply, english_reply, audio_base64, intent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, sender, kannada_reply, english_reply, audio_base64, intent))

    msg_id = cur.lastrowid
    conn.commit()
    conn.close()
    return msg_id


def get_chat_history(session_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve chat history for a session."""
    init_chat_tables()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM chat_messages
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT ?
    """, (session_id, limit))

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_farmer_memory(session_id: str, key: str, value: Any) -> None:
    """Save an extracted fact or memory element for the farmer session."""
    init_chat_tables()
    conn = get_db()
    cur = conn.cursor()

    val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)

    cur.execute("""
        INSERT INTO farmer_memory (session_id, memory_key, memory_value, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id, memory_key) DO UPDATE SET
            memory_value = excluded.memory_value,
            updated_at = CURRENT_TIMESTAMP
    """, (session_id, key, val_str))

    conn.commit()
    conn.close()


def get_all_farmer_memory(session_id: str) -> Dict[str, Any]:
    """Retrieve all stored memory entities for the farmer session."""
    init_chat_tables()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT memory_key, memory_value FROM farmer_memory WHERE session_id = ?", (session_id,))
    rows = cur.fetchall()
    conn.close()

    result = {}
    for r in rows:
        val = r["memory_value"]
        try:
            result[r["memory_key"]] = json.loads(val)
        except Exception:
            result[r["memory_key"]] = val
    return result
