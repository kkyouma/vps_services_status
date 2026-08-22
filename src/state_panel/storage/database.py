"""SQLite storage manager for checks and metrics."""

import random
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from state_panel.probes.base import CheckResult


class Database:
    """SQLite database manager for state-panel."""

    def __init__(self, db_path: str | Path = "state_panel.db") -> None:
        self.db_path = Path(db_path)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    status_code INTEGER,
                    message TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checks_service_timestamp
                ON checks(service_id, timestamp)
            """)
            conn.commit()

    def save_check(self, result: CheckResult) -> None:
        """Persist a single check result."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO checks (
                    service_id, service_name, status, latency_ms,
                    status_code, message, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.service_id,
                    result.service_name,
                    result.status,
                    result.latency_ms,
                    result.status_code,
                    result.message,
                    result.timestamp.isoformat(),
                ),
            )
            conn.commit()

    def save_checks(self, results: list[CheckResult]) -> None:
        """Persist multiple check results in a single transaction."""
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO checks (
                    service_id, service_name, status, latency_ms,
                    status_code, message, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.service_id,
                        r.service_name,
                        r.status,
                        r.latency_ms,
                        r.status_code,
                        r.message,
                        r.timestamp.isoformat(),
                    )
                    for r in results
                ],
            )
            conn.commit()

    def get_latest_status(self, service_id: str) -> str | None:
        """Get the most recent status for a given service."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT status FROM checks
                WHERE service_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (service_id,),
            )
            row = cursor.fetchone()
            return row["status"] if row else None

    def get_checks_since(
        self, service_id: str, since: datetime
    ) -> list[dict[str, Any]]:
        """Retrieve all checks for a service since a specific datetime."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM checks
                WHERE service_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (service_id, since.isoformat()),
            )
            return [dict(row) for row in cursor.fetchall()]

    def seed_mock_history(
        self,
        service_configs: list[dict[str, str]],
        days: int = 90,
        checks_per_day: int = 24,
    ) -> None:
        """Seed realistic historical data for instant visual preview."""
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days)
        records: list[tuple[Any, ...]] = []

        for service in service_configs:
            srv_id = service["id"]
            srv_name = service["name"]

            # Generate hourly checks for the past N days
            current_time = start_date
            while current_time <= now:
                # 98.5% chance operational, 1.0% degraded, 0.5% down
                roll = random.random()  # noqa: S311
                if roll > 0.015:
                    status = "operational"
                    latency = round(random.uniform(15.0, 65.0), 2)  # noqa: S311
                    code = 200
                    msg = "HTTP 200 OK"
                elif roll > 0.005:
                    status = "degraded"
                    latency = round(random.uniform(250.0, 1200.0), 2)  # noqa: S311
                    code = 200
                    msg = "High latency detected"
                else:
                    status = "down"
                    latency = 0.0
                    code = 502
                    msg = "502 Bad Gateway"

                records.append(
                    (
                        srv_id,
                        srv_name,
                        status,
                        latency,
                        code,
                        msg,
                        current_time.isoformat(),
                    )
                )
                current_time += timedelta(hours=24 / checks_per_day)

        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO checks (
                    service_id, service_name, status, latency_ms,
                    status_code, message, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()
