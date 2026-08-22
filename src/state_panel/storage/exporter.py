"""Exporter module to generate static JSON for Cloudflare Pages."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from state_panel.config import PanelConfig
from state_panel.probes.base import CheckResult
from state_panel.storage.aggregator import Aggregator


class Exporter:
    """Exports status and historical timeline into static JSON format."""

    def __init__(self, config: PanelConfig, aggregator: Aggregator) -> None:
        self.config = config
        self.aggregator = aggregator

    def generate_status_payload(
        self, current_results: list[CheckResult]
    ) -> dict[str, Any]:
        """Build status payload matching Cloudflare Pages Vue UI schema."""
        now = datetime.now(UTC)
        results_by_id = {r.service_id: r for r in current_results}

        # Calculate overall status
        statuses = [r.status for r in current_results]
        if any(s == "down" for s in statuses):
            overall_status = "major_outage"
        elif any(s == "degraded" for s in statuses):
            overall_status = "degraded"
        else:
            overall_status = "operational"

        services_data: list[dict[str, Any]] = []

        for srv in self.config.services:
            res = results_by_id.get(srv.id)
            history_data = self.aggregator.get_service_history(
                srv.id, days=self.config.settings.history_days
            )

            services_data.append(
                {
                    "id": srv.id,
                    "name": srv.name,
                    "category": srv.category,
                    "description": srv.description,
                    "type": srv.type,
                    "current_status": res.status if res else "unknown",
                    "current_latency_ms": res.latency_ms if res else 0.0,
                    "current_message": res.message if res else "",
                    "uptime_percentage": history_data["uptime_percentage"],
                    "uptime_30d_percentage": history_data["uptime_30d_percentage"],
                    "uptime_90d_percentage": history_data["uptime_90d_percentage"],
                    "history": history_data["history"],
                }
            )

        return {
            "title": self.config.settings.title,
            "description": self.config.settings.description,
            "last_updated": now.isoformat(),
            "overall_status": overall_status,
            "history_days": self.config.settings.history_days,
            "services": services_data,
        }

    def export_to_file(
        self,
        current_results: list[CheckResult],
        target_path: str | Path | None = None,
    ) -> Path:
        """Write status JSON to target file location."""
        dest = (
            Path(target_path)
            if target_path
            else Path(self.config.settings.output_dir) / "status.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)

        payload = self.generate_status_payload(current_results)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return dest
