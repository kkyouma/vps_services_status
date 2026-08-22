"""ntfy.sh Pub/Sub alert publisher."""

import httpx

from state_panel.config import NtfyConfig, ServiceConfig
from state_panel.probes.base import CheckResult


class NtfyNotifier:
    """Sends notifications via ntfy HTTP API (Pub/Sub)."""

    def __init__(self, config: NtfyConfig) -> None:
        self.config = config

    async def send_status_change(
        self,
        service: ServiceConfig,
        prev_status: str | None,
        result: CheckResult,
    ) -> bool:
        """Publish status change notification to ntfy topic."""
        if not self.config.enabled or not self.config.topic:
            return False

        # Determine title, tags and priority based on status transition
        if result.status == "down":
            title = f"🚨 Service Down: {service.name}"
            tags = "skull,warning"
            priority = str(max(self.config.priority, 4))
            body = (
                f"**{service.name}** is DOWN.\n\n"
                f"• **Error**: {result.message}\n"
                f"• **Latency**: {result.latency_ms} ms\n"
                f"• **Category**: {service.category}"
            )
        elif result.status == "operational" and prev_status in ("down", "degraded"):
            title = f"✅ Service Restored: {service.name}"
            tags = "white_check_mark"
            priority = "3"
            body = (
                f"**{service.name}** is back OPERATIONAL.\n\n"
                f"• **Status**: {result.message}\n"
                f"• **Latency**: {result.latency_ms} ms"
            )
        elif result.status == "degraded" and prev_status != "degraded":
            title = f"⚠️ Service Degraded: {service.name}"
            tags = "warning"
            priority = "3"
            body = (
                f"**{service.name}** is experiencing DEGRADED performance.\n\n"
                f"• **Notice**: {result.message}\n"
                f"• **Latency**: {result.latency_ms} ms"
            )
        else:
            return False

        url = f"{self.config.server.rstrip('/')}/{self.config.topic}"
        headers: dict[str, str] = {
            "Title": title,
            "Priority": priority,
            "Tags": tags,
            "Markdown": "yes",
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url, content=body.encode("utf-8"), headers=headers
                )
                return resp.is_success
        except Exception:  # noqa: BLE001
            # Do not crash the monitoring engine if notification fails
            return False
