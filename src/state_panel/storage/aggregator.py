"""Historical aggregator for 30-day status timeline and hourly metrics."""

from datetime import UTC, datetime, timedelta
from typing import Any

from state_panel.storage.database import Database


class HourMetric:
    """Metric for a single hour (0..23) within a day."""

    def __init__(self, hour: int) -> None:
        self.hour = hour
        self.total_checks = 0
        self.operational_checks = 0
        self.degraded_checks = 0
        self.down_checks = 0
        self.total_latency = 0.0
        self.min_latency_ms: float | None = None
        self.max_latency_ms: float | None = None
        self.checks: list[dict[str, Any]] = []

    @property
    def status(self) -> str:
        """Status observed during the hour based on down percentage."""
        if self.total_checks == 0:
            return "nodata"
        if self.down_checks == 0 and self.degraded_checks == 0:
            return "operational"
        # If > 25% down checks -> down, otherwise degraded
        if (self.down_checks / self.total_checks) > 0.25:
            return "down"
        return "degraded"

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency for the hour."""
        if self.total_checks == 0:
            return 0.0
        return round(self.total_latency / self.total_checks, 2)

    def add_check(
        self,
        ts_str: str,
        status: str,
        latency_ms: float,
        status_code: int | None = None,
        message: str = "",
    ) -> None:
        """Record a single check result in this hour."""
        self.total_checks += 1
        self.total_latency += latency_ms
        if self.min_latency_ms is None or latency_ms < self.min_latency_ms:
            self.min_latency_ms = round(latency_ms, 2)
        if self.max_latency_ms is None or latency_ms > self.max_latency_ms:
            self.max_latency_ms = round(latency_ms, 2)

        if status == "operational":
            self.operational_checks += 1
        elif status == "degraded":
            self.degraded_checks += 1
        else:
            self.down_checks += 1

        self.checks.append(
            {
                "timestamp": ts_str,
                "latency_ms": round(latency_ms, 2),
                "status": status,
                "status_code": status_code,
                "message": message,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert hour metrics to dictionary format."""
        return {
            "hour": self.hour,
            "status": self.status,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": (
                self.min_latency_ms if self.min_latency_ms is not None else 0.0
            ),
            "max_latency_ms": (
                self.max_latency_ms if self.max_latency_ms is not None else 0.0
            ),
            "checks_count": self.total_checks,
            "down_checks": self.down_checks,
            "degraded_checks": self.degraded_checks,
            "checks": self.checks,
        }


class DayMetric:
    """Metric for a single day in the history bar with hourly breakdown."""

    def __init__(self, date_str: str) -> None:
        self.date = date_str
        self.total_checks = 0
        self.operational_checks = 0
        self.degraded_checks = 0
        self.down_checks = 0
        self.total_latency = 0.0
        self.min_latency_ms: float | None = None
        self.max_latency_ms: float | None = None
        self.hours = [HourMetric(h) for h in range(24)]

    @property
    def status(self) -> str:
        """Status observed during the day based on down percentage."""
        if self.total_checks == 0:
            return "nodata"
        if self.down_checks == 0 and self.degraded_checks == 0:
            return "operational"
        if (self.down_checks / self.total_checks) > 0.25:
            return "down"
        return "degraded"

    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime percentage for the day."""
        if self.total_checks == 0:
            return 100.0
        # Operational counts as 1.0, degraded as 0.5, down as 0.0
        score = self.operational_checks + (self.degraded_checks * 0.5)
        return round((score / self.total_checks) * 100, 2)

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency for the day."""
        if self.total_checks == 0:
            return 0.0
        return round(self.total_latency / self.total_checks, 2)

    def add_check(
        self,
        ts_str: str,
        status: str,
        latency_ms: float,
        status_code: int | None = None,
        message: str = "",
    ) -> None:
        """Add check to day and appropriate hour metric."""
        self.total_checks += 1
        self.total_latency += latency_ms
        if self.min_latency_ms is None or latency_ms < self.min_latency_ms:
            self.min_latency_ms = round(latency_ms, 2)
        if self.max_latency_ms is None or latency_ms > self.max_latency_ms:
            self.max_latency_ms = round(latency_ms, 2)

        if status == "operational":
            self.operational_checks += 1
        elif status == "degraded":
            self.degraded_checks += 1
        else:
            self.down_checks += 1

        # Determine hour (0..23)
        try:
            time_part = ts_str.split("T")[1] if "T" in ts_str else ts_str.split(" ")[1]
            hour = int(time_part.split(":")[0])
            if 0 <= hour <= 23:
                self.hours[hour].add_check(
                    ts_str, status, latency_ms, status_code, message
                )
        except (IndexError, ValueError):
            pass

    def to_dict(self) -> dict[str, Any]:
        """Convert day metrics to dictionary format."""
        return {
            "date": self.date,
            "status": self.status,
            "uptime_percentage": self.uptime_percentage,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": (
                self.min_latency_ms if self.min_latency_ms is not None else 0.0
            ),
            "max_latency_ms": (
                self.max_latency_ms if self.max_latency_ms is not None else 0.0
            ),
            "total_checks": self.total_checks,
            "down_checks": self.down_checks,
            "degraded_checks": self.degraded_checks,
            "hours": [h.to_dict() for h in self.hours],
        }


class Aggregator:
    """Aggregates checks into 30-day timelines and overall uptime metrics."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_service_history(self, service_id: str, days: int = 30) -> dict[str, Any]:
        """Generate daily breakdown and total uptime for a service."""
        now = datetime.now(UTC)
        start_date = (now - timedelta(days=days - 1)).date()

        # Pre-populate all days in range with empty DayMetrics
        day_map: dict[str, DayMetric] = {}
        for i in range(days):
            d = (start_date + timedelta(days=i)).isoformat()
            day_map[d] = DayMetric(d)

        # Retrieve raw checks
        since = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        checks = self.db.get_checks_since(service_id, since)

        total_checks_all = len(checks)
        total_score_all = 0.0

        for check in checks:
            ts_str = check["timestamp"]
            check_date = ts_str.split("T")[0] if "T" in ts_str else ts_str.split(" ")[0]
            if check_date in day_map:
                st = check["status"]
                lat = float(check["latency_ms"])
                code = check.get("status_code")
                msg = check.get("message") or ""
                day_map[check_date].add_check(ts_str, st, lat, code, msg)

                if st == "operational":
                    total_score_all += 1.0
                elif st == "degraded":
                    total_score_all += 0.5

        # Calculate overall uptime
        uptime_pct = (
            round((total_score_all / total_checks_all) * 100, 2)
            if total_checks_all > 0
            else 100.0
        )

        history_list = [day_map[d].to_dict() for d in sorted(day_map.keys())]

        return {
            "service_id": service_id,
            "uptime_percentage": uptime_pct,
            "uptime_30d_percentage": uptime_pct,
            "uptime_90d_percentage": uptime_pct,
            "total_checks": total_checks_all,
            "total_checks_90d": total_checks_all,
            "history": history_list,
        }
