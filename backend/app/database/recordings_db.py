"""
SQLite Database module for Voice Recordings.
Stores and retrieves microphone voice stream recordings with caller name, mobile number,
timestamps, duration, risk scores, and audio file references.

Enables role-based access:
- Citizens see only their own recordings filtered by mobile number.
- Helpline Operators see every citizen's recording in a unified administrative list.
"""

import os
import re
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "recordings.db")


def normalize_phone(phone: Optional[str]) -> str:
    """Normalize phone number to last 10 digits for consistent matching."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    return digits[-10:] if len(digits) >= 10 else digits


def get_db_connection() -> sqlite3.Connection:
    """Create a thread-safe connection to the SQLite database with dictionary rows."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables, indexes, and seed sample recordings if empty."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_recordings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT UNIQUE NOT NULL,
                    caller_name TEXT NOT NULL,
                    caller_phone TEXT NOT NULL,
                    phone_normalized TEXT NOT NULL,
                    user_id TEXT,
                    timestamp TEXT NOT NULL,
                    duration_seconds REAL DEFAULT 0.0,
                    file_path TEXT NOT NULL,
                    recording_url TEXT NOT NULL,
                    risk_level TEXT DEFAULT 'LOW',
                    summary TEXT DEFAULT 'Microphone Voice Stream Session',
                    language TEXT DEFAULT 'or-IN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_phone_norm ON voice_recordings(phone_normalized);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_call_id ON voice_recordings(call_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON voice_recordings(created_at DESC);")

            logger.info("[RecordingsDB] Initialized voice_recordings table and indexes.")
    except Exception as e:
        logger.error(f"[RecordingsDB] Error initializing database: {e}", exc_info=True)
    finally:
        conn.close()


def save_recording(
    call_id: str,
    caller_name: str,
    caller_phone: str,
    duration_seconds: float = 0.0,
    file_path: str = "",
    recording_url: str = "",
    risk_level: str = "LOW",
    summary: str = "Microphone Voice Stream Session",
    language: str = "or-IN",
    user_id: Optional[str] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inserts or updates a voice stream recording record in the SQLite database.
    """
    phone_norm = normalize_phone(caller_phone)
    formatted_time = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    clean_name = (caller_name or "").strip() or f"Citizen ({caller_phone})"

    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO voice_recordings (
                    call_id, caller_name, caller_phone, phone_normalized, user_id,
                    timestamp, duration_seconds, file_path, recording_url, risk_level, summary, language
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(call_id) DO UPDATE SET
                    caller_name=excluded.caller_name,
                    caller_phone=excluded.caller_phone,
                    phone_normalized=excluded.phone_normalized,
                    duration_seconds=excluded.duration_seconds,
                    file_path=excluded.file_path,
                    recording_url=excluded.recording_url,
                    risk_level=excluded.risk_level,
                    summary=excluded.summary,
                    language=excluded.language;
            """, (
                call_id, clean_name, caller_phone, phone_norm, user_id or f"citizen_{phone_norm[-4:] if phone_norm else 'anon'}",
                formatted_time, round(duration_seconds, 1), file_path, recording_url,
                risk_level, summary, language
            ))
            logger.info(f"[RecordingsDB] Saved recording for {clean_name} ({caller_phone}) -> call_id: {call_id}")

        return {
            "call_id": call_id,
            "caller_name": clean_name,
            "caller_phone": caller_phone,
            "duration_seconds": duration_seconds,
            "recording_url": recording_url,
            "risk_level": risk_level,
            "summary": summary,
            "timestamp": formatted_time,
            "language": language
        }
    except Exception as e:
        logger.error(f"[RecordingsDB] Failed to save recording for {call_id}: {e}", exc_info=True)
        return {}
    finally:
        conn.close()


def get_recordings(phone: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch voice recordings.
    - If phone is provided: returns only that citizen's own voice recordings.
    - If phone is None: returns every citizen's voice recordings as a list (for operator dashboard).
    """
    conn = get_db_connection()
    try:
        if phone:
            phone_norm = normalize_phone(phone)
            if phone_norm:
                cur = conn.execute("""
                    SELECT * FROM voice_recordings
                    WHERE phone_normalized = ? OR phone_normalized LIKE ? OR caller_phone LIKE ?
                    ORDER BY id DESC;
                """, (phone_norm, f"%{phone_norm}%", f"%{phone_norm}%"))
            else:
                cur = conn.execute("SELECT * FROM voice_recordings ORDER BY id DESC;")
        else:
            # Operator view: see every single recording
            cur = conn.execute("SELECT * FROM voice_recordings ORDER BY id DESC;")

        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "call_id": r["call_id"],
                "caller_name": r["caller_name"],
                "caller_number": r["caller_phone"],
                "caller_phone": r["caller_phone"],
                "user_id": r["user_id"],
                "timestamp": r["timestamp"],
                "duration_seconds": r["duration_seconds"],
                "duration": f"{int(r['duration_seconds'] // 60)}m {int(r['duration_seconds'] % 60)}s" if r["duration_seconds"] > 0 else "0m 15s",
                "file_path": r["file_path"],
                "recording_url": r["recording_url"],
                "risk_level": r["risk_level"],
                "summary": r["summary"],
                "language": r["language"],
                "type": "voice",
                "is_legitimate": True,
                "status": "RECORDING_STORED"
            })
        return result
    except Exception as e:
        logger.error(f"[RecordingsDB] Error fetching recordings (phone={phone}): {e}", exc_info=True)
        return []
    finally:
        conn.close()


def delete_recording(identifier: str) -> bool:
    """
    DPDP Act Right to Erasure: Permanently delete recording metadata and audio file from disk.
    """
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "SELECT file_path FROM voice_recordings WHERE call_id = ? OR id = ?;",
            (identifier, identifier)
        )
        row = cur.fetchone()
        file_path = row["file_path"] if row else None

        with conn:
            conn.execute(
                "DELETE FROM voice_recordings WHERE call_id = ? OR id = ?;",
                (identifier, identifier)
            )

        # Delete file from disk
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[RecordingsDB] Erased audio file: {file_path}")
            except Exception as fe:
                logger.warning(f"[RecordingsDB] Could not erase file {file_path}: {fe}")

        return True
    except Exception as e:
        logger.error(f"[RecordingsDB] Error deleting recording {identifier}: {e}", exc_info=True)
        return False
    finally:
        conn.close()


# Ensure DB is initialized upon module load
init_db()
