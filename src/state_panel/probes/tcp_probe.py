"""TCP Port probe implementation using asyncio streams."""

import asyncio
import time

from state_panel.config import ServiceConfig
from state_panel.probes.base import BaseProbe, CheckResult


class TcpProbe(BaseProbe):
    """Probe for raw TCP ports (databases, redis, custom sockets)."""

    def __init__(self, service: ServiceConfig) -> None:
        self.service = service

    async def check(self) -> CheckResult:
        """Attempt to open a TCP connection to host:port."""
        host = self.service.host or "127.0.0.1"
        port = self.service.port

        if not port:
            return CheckResult(
                service_id=self.service.id,
                service_name=self.service.name,
                service_category=self.service.category,
                status="down",
                latency_ms=0.0,
                message="Missing target port in configuration",
            )

        start_time = time.perf_counter()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.service.timeout,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000
            writer.close()
            await writer.wait_closed()

            return CheckResult(
                service_id=self.service.id,
                service_name=self.service.name,
                service_category=self.service.category,
                status="operational",
                latency_ms=round(latency_ms, 2),
                message=f"TCP port {port} open",
            )
        except TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                service_id=self.service.id,
                service_name=self.service.name,
                service_category=self.service.category,
                status="down",
                latency_ms=round(latency_ms, 2),
                message=f"TCP connection timed out after {self.service.timeout}s",
            )
        except OSError as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                service_id=self.service.id,
                service_name=self.service.name,
                service_category=self.service.category,
                status="down",
                latency_ms=round(latency_ms, 2),
                message=f"Connection refused / error: {exc.strerror or exc}",
            )
