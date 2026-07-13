import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import ARENA_EVIDENCE_STATE_DB


@dataclass(frozen=True)
class ArenaEvidenceSession:
    telegram_id: int
    match_id: int
    screenshot_file_id: str | None
    video_file_id: str | None

    @property
    def complete(self) -> bool:
        return bool(self.screenshot_file_id and self.video_file_id)


class DuplicateEvidenceError(ValueError):
    pass


class ArenaEvidenceStore:
    def __init__(self, database_path: str = ARENA_EVIDENCE_STATE_DB):
        self.database_path = str(Path(database_path))
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_evidence_sessions (
                    telegram_id INTEGER PRIMARY KEY,
                    match_id INTEGER NOT NULL,
                    screenshot_file_id TEXT,
                    video_file_id TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def start(self, telegram_id: int, match_id: int) -> ArenaEvidenceSession:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM arena_evidence_sessions WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
            if existing and existing["match_id"] == match_id:
                return self._from_row(existing)
            connection.execute(
                """
                INSERT INTO arena_evidence_sessions
                    (telegram_id, match_id, screenshot_file_id, video_file_id, updated_at)
                VALUES (?, ?, NULL, NULL, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    match_id = excluded.match_id,
                    screenshot_file_id = NULL,
                    video_file_id = NULL,
                    updated_at = excluded.updated_at
                """,
                (telegram_id, match_id, now),
            )
        return self.get(telegram_id)

    def get(self, telegram_id: int) -> ArenaEvidenceSession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM arena_evidence_sessions WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def mark_accepted(
        self, telegram_id: int, *, media_type: str, file_id: str
    ) -> ArenaEvidenceSession:
        session = self.get(telegram_id)
        if not session:
            raise ValueError("Evidence session topilmadi")
        if media_type == "screenshot":
            if session.screenshot_file_id:
                raise DuplicateEvidenceError("Screenshot allaqachon yuborilgan")
            column = "screenshot_file_id"
        elif media_type == "video":
            if session.video_file_id:
                raise DuplicateEvidenceError("Video allaqachon yuborilgan")
            column = "video_file_id"
        else:
            raise ValueError("Noto‘g‘ri evidence turi")
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                f"UPDATE arena_evidence_sessions SET {column} = ?, updated_at = ? "
                "WHERE telegram_id = ?",
                (file_id, now, telegram_id),
            )
        return self.get(telegram_id)

    def clear(self, telegram_id: int):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM arena_evidence_sessions WHERE telegram_id = ?",
                (telegram_id,),
            )

    @staticmethod
    def _from_row(row) -> ArenaEvidenceSession:
        return ArenaEvidenceSession(
            telegram_id=row["telegram_id"],
            match_id=row["match_id"],
            screenshot_file_id=row["screenshot_file_id"],
            video_file_id=row["video_file_id"],
        )


evidence_store = ArenaEvidenceStore()
