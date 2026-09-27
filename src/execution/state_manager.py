import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

DB_PATH = Path.home() / "quant_pipeline" / "data" / "state.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class StateManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Active positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    is_long INTEGER NOT NULL,
                    weight REAL NOT NULL,
                    size REAL NOT NULL,
                    entry_px REAL NOT NULL,
                    stop_px REAL NOT NULL,
                    atr REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Key-value store for HMM distribution, IC history, equity watermarks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def upsert_position(self, symbol: str, is_long: bool, weight: float, size: float, 
                        entry_px: float, stop_px: float, atr: float):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.cursor().execute("""
                INSERT INTO positions (symbol, is_long, weight, size, entry_px, stop_px, atr, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    is_long = excluded.is_long,
                    weight = excluded.weight,
                    size = excluded.size,
                    entry_px = excluded.entry_px,
                    stop_px = excluded.stop_px,
                    atr = excluded.atr,
                    updated_at = excluded.updated_at
            """, (symbol, 1 if is_long else 0, weight, size, entry_px, stop_px, atr, now))
            conn.commit()

    def delete_position(self, symbol: str):
        with self._get_conn() as conn:
            conn.cursor().execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
            conn.commit()

    def clear_all_positions(self):
        with self._get_conn() as conn:
            conn.cursor().execute("DELETE FROM positions")
            conn.commit()

    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, is_long, weight, size, entry_px, stop_px, atr, updated_at FROM positions")
            rows = cursor.fetchall()
            return {
                r[0]: {
                    "symbol": r[0], "is_long": bool(r[1]), "weight": r[2], "size": r[3],
                    "entry_px": r[4], "stop_px": r[5], "atr": r[6], "updated_at": r[7]
                } for r in rows
            }

    def set_meta(self, key: str, value: Any):
        now = datetime.now(timezone.utc).isoformat()
        val_str = json.dumps(value)
        with self._get_conn() as conn:
            conn.cursor().execute("""
                INSERT INTO metadata (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, val_str, now))
            conn.commit()

    def get_meta(self, key: str, default: Optional[Any] = None) -> Any:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default
