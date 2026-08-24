"""Storage manager supporting both local SQLite and remote Turso (libSQL)."""

import os
import random
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import libsql_client

from state_panel.probes.base import CheckResult


class Database:
    """Database manager supporting both local SQLite and remote Turso libSQL."""

    def __init__(
        self,
        db_path: str | Path = "state_panel.db",
        turso_url: str | None = None,
        turso_token: str | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.turso_url = turso_url or os.environ.get("TURSO_DATABASE_URL")
        self.turso_token = turso_token or os.environ.get("TURSO_AUTH_TOKEN")
        self.is_turso = bool(self.turso_url and self.turso_token)

        # Normalize Turso URL to HTTPS for robust connection
        if self.turso_url and self.turso_url.startswith("libsql://"):
            self.turso_url = self.turso_url.replace("libsql://", "https://")

        self.init_db()

    def _get_turso_client(self) -> libsql_client.ClientSync:
        """Create a sync Turso libSQL client."""
        return libsql_client.create_client_sync(
            url=self.turso_url,
            auth_token=self.turso_token,
        )

    def _get_sqlite_connection(self) -> sqlite3.Connection:
        """Create a local SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        create_table_sql = """
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
        """
        create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_checks_service_timestamp
            ON checks(service_id, timestamp)
        """

        if self.is_turso:
            client = self._get_turso_client()
            try:
                client.execute(create_table_sql)
                client.execute(create_index_sql)
            finally:
                client.close()
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_sqlite_connection() as conn:
                conn.execute(create_table_sql)
                conn.execute(create_index_sql)
                conn.commit()

    def save_check(self, result: CheckResult) -> None:
        """Persist a single check result."""
        sql = """
            INSERT INTO checks (
                service_id, service_name, status, latency_ms,
                status_code, message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            result.service_id,
            result.service_name,
            result.status,
            result.latency_ms,
            result.status_code,
            result.message,
            result.timestamp.isoformat(),
        )

        if self.is_turso:
            client = self._get_turso_client()
            try:
                client.execute(sql, list(params))
            finally:
                client.close()
        else:
            with self._get_sqlite_connection() as conn:
                conn.execute(sql, params)
                conn.commit()

    def save_checks(self, results: list[CheckResult]) -> None:
        """Persist multiple check results."""
        if not results:
            return

        sql = """
            INSERT INTO checks (
                service_id, service_name, status, latency_ms,
                status_code, message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
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
        ]

        if self.is_turso:
            client = self._get_turso_client()
            try:
                stmts: list[libsql_client.InStatement] = [
                    libsql_client.Statement(sql, list(row)) for row in rows
                ]
                client.batch(stmts)
            finally:
                client.close()
        else:
            with self._get_sqlite_connection() as conn:
                conn.executemany(sql, rows)
                conn.commit()

    def get_latest_status(self, service_id: str) -> str | None:
        """Get the most recent status for a given service."""
        sql = """
            SELECT status FROM checks
            WHERE service_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """
        if self.is_turso:
            client = self._get_turso_client()
            try:
                res = client.execute(sql, [service_id])
                if res.rows:
                    return str(res.rows[0]["status"])
                return None
            finally:
                client.close()
        else:
            with self._get_sqlite_connection() as conn:
                cursor = conn.execute(sql, (service_id,))
                row = cursor.fetchone()
                return row["status"] if row else None

    def get_checks_since(
        self, service_id: str, since: datetime
    ) -> list[dict[str, Any]]:
        """Retrieve all checks for a service since a specific datetime."""
        sql = """
            SELECT * FROM checks
            WHERE service_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """
        since_str = since.isoformat()

        if self.is_turso:
            client = self._get_turso_client()
            try:
                res = client.execute(sql, [service_id, since_str])
                return [r.asdict() for r in res.rows]
            finally:
                client.close()
        else:
            with self._get_sqlite_connection() as conn:
                cursor = conn.execute(sql, (service_id, since_str))
                return [dict(row) for row in cursor.fetchall()]

    def prune_old_checks(self, days: int = 90) -> int:
        """Delete check records older than N days to keep database lean."""
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        sql = """
            DELETE FROM checks
            WHERE timestamp < ?
        """
        if self.is_turso:
            client = self._get_turso_client()
            try:
                res = client.execute(sql, [cutoff])
                return res.rows_affected
            finally:
                client.close()
        else:
            with self._get_sqlite_connection() as conn:
                cursor = conn.execute(sql, (cutoff,))
                conn.commit()
                return cursor.rowcount

    def reset_db(self) -> None:
        """Clear all records from checks table."""
        if self.is_turso:
            client = self._get_turso_client()
            try:
                client.execute("DELETE FROM checks")
            finally:
                client.close()
        else:
            if self.db_path.exists():
                self.db_path.unlink()
            self.init_db()

    def seed_mock_history(
        self,
        service_configs: list[dict[str, str]],
        days: int = 90,
        checks_per_day: int = 24,
    ) -> None:
        """Seed realistic historical data for visual preview."""
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days)
        records: list[list[Any]] = []

        for service in service_configs:
            srv_id = service["id"]
            srv_name = service["name"]

            current_time = start_date
            while current_time <= now:
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
                    [
                        srv_id,
                        srv_name,
                        status,
                        latency,
                        code,
                        msg,
                        current_time.isoformat(),
                    ]
                )
                current_time += timedelta(hours=24 / checks_per_day)

        insert_sql = """
            INSERT INTO checks (
                service_id, service_name, status, latency_ms,
                status_code, message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        if self.is_turso:
            client = self._get_turso_client()
            try:
                for service in service_configs:
                    client.execute(
                        "DELETE FROM checks WHERE service_id = ?",
                        [service["id"]],
                    )
                chunk_size = 500
                for i in range(0, len(records), chunk_size):
                    chunk = records[i : i + chunk_size]
                    stmts: list[libsql_client.InStatement] = [
                        libsql_client.Statement(insert_sql, row) for row in chunk
                    ]
                    client.batch(stmts)
            finally:
                client.close()
        else:
            with self._get_sqlite_connection() as conn:
                for service in service_configs:
                    conn.execute(
                        "DELETE FROM checks WHERE service_id = ?",
                        (service["id"],),
                    )
                conn.executemany(insert_sql, records)
                conn.commit()
