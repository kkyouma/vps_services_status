"""Engine orchestrator for executing probes, persisting data, and alerting."""

import asyncio
from pathlib import Path

from state_panel.config import PanelConfig
from state_panel.notifier.ntfy import NtfyNotifier
from state_panel.probes.base import CheckResult
from state_panel.probes.registry import get_probe
from state_panel.storage.aggregator import Aggregator
from state_panel.storage.database import Database
from state_panel.storage.exporter import Exporter


class Engine:
    """Core engine coordinating checks, persistence, alerts, and export."""

    def __init__(self, config: PanelConfig) -> None:
        self.config = config
        self.db = Database(config.settings.db_path)
        self.aggregator = Aggregator(self.db)
        self.exporter = Exporter(self.config, self.aggregator)
        self.notifier = NtfyNotifier(self.config.ntfy)

    async def run_checks(self) -> list[CheckResult]:
        """Execute all configured service probes concurrently."""
        if not self.config.services:
            return []

        probes = [get_probe(srv) for srv in self.config.services]
        results: list[CheckResult] = await asyncio.gather(
            *[p.check() for p in probes], return_exceptions=False
        )

        # Detect status changes and notify
        services_by_id = {s.id: s for s in self.config.services}
        notify_tasks = []

        for result in results:
            srv = services_by_id.get(result.service_id)
            if not srv:
                continue

            prev_status = self.db.get_latest_status(result.service_id)
            if prev_status is not None and prev_status != result.status:
                notify_tasks.append(
                    self.notifier.send_status_change(
                        service=srv,
                        prev_status=prev_status,
                        result=result,
                    )
                )

        if notify_tasks:
            await asyncio.gather(*notify_tasks, return_exceptions=True)

        # Save check results to SQLite
        self.db.save_checks(results)

        return results

    async def run_and_export(
        self, target_path: str | Path | None = None
    ) -> tuple[list[CheckResult], Path]:
        """Run checks, persist, and export status JSON."""
        results = await self.run_checks()
        out_path = self.exporter.export_to_file(results, target_path)
        return results, out_path
