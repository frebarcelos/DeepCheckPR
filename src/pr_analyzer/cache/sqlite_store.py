"""Cache persistente key-value com SQLite + WAL mode.

LLM-10: backend alternativo ao JSON para sobreviver a Docker rebuilds.
WAL mode permite múltiplos leitores simultâneos sem lock; escritas serializam.
check_same_thread=False permite uma instância ser compartilhada entre threads.
"""

import sqlite3
import threading
from pathlib import Path


class SqliteKVStore:
    """Key-value store persistente com SQLite; seguro para acesso multi-thread."""

    def __init__(self, db_path: Path, table: str = "classifications") -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._table = table
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(db_path), check_same_thread=False, timeout=10
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._conn.commit()

    def get(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                f"SELECT value FROM {self._table} WHERE key = ?", (key,)
            ).fetchone()
        return str(row[0]) if row else None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                f"INSERT OR REPLACE INTO {self._table} (key, value) VALUES (?, ?)",
                (key, value),
            )
            self._conn.commit()

    def __len__(self) -> int:
        with self._lock:
            row = self._conn.execute(f"SELECT COUNT(*) FROM {self._table}").fetchone()
        return int(row[0])
