"""Historical aggregator for 90-day status timeline and uptime calculations."""

from datetime import UTC, datetime, timedelta
from typing import Any

from state_panel.storage.database import Database


class DayMetric:
    """Metric for a single day in the history bar."""

    def __init__(self, date_str: str) -> None:
        self.date = date_str
        self.total_checks = 0
        self.operational_checks = 0
        self.degraded_checks = 0
        self.down_checks = 0
        self.total_latency = 0.0

    @property
    def status(self) -> str:
        """Worst status observed during the day."""
        if self.total_checks == 0:
            return "nodata"
        if self.down_checks > 0:
            return "down"
        if self.degraded_checks > 0:
            return "degraded"
        return "operational"

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "status": self.status,
            "uptime_percentage": self.uptime_percentage,
            "avg_latency_ms": self.avg_latency_ms,
            "total_checks": self.total_checks,
            "down_checks": self.down_checks,
            "degraded_checks": self.degraded_checks,
        }


class Aggregator:
    """Aggregates checks into 90-day timelines and overall uptime metrics."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_service_history(self, service_id: str, days: int = 90) -> dict[str, Any]:
        """Generate 90-day daily breakdown and total uptime for a service."""
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
            # Parse timestamp date
            ts_str = check["timestamp"]
            check_date = ts_str.split("T")[0]
            if check_date in day_map:
                metric = day_map[check_date]
                metric.total_checks += 1
                metric.total_latency += check["latency_ms"]

                st = check["status"]
                if st == "operational":
                    metric.operational_checks += 1
                    total_score_all += 1.0
                elif st == "degraded":
                    metric.degraded_checks += 1
                    total_score_all += 0.5
                else:
                    metric.down_checks += 1

        # Calculate overall 90-day uptime
        uptime_90d = (
            round((total_score_all / total_checks_all) * 100, 2)
            if total_checks_all > 0
            else 100.0
        )

        history_list = [day_map[d].to_dict() for d in sorted(day_map.keys())]

        return {
            "service_id": service_id,
            "uptime_90d_percentage": uptime_90d,
            "total_checks_90d": total_checks_all,
            "history": history_list,
        }
