"""HTTP/HTTPS probe implementation using httpx."""

import time

import httpx

from state_panel.config import ServiceConfig
from state_panel.probes.base import BaseProbe, CheckResult, CheckStatus


class HttpProbe(BaseProbe):
    """Probe for HTTP/HTTPS endpoints."""

    def __init__(self, service: ServiceConfig) -> None:
        self.service = service

    async def check(self) -> CheckResult:
        """Perform an HTTP request and measure latency."""
        url = self.service.target
        if not url:
            return CheckResult(
                service_id=self.service.id,
                service_name=self.service.name,
                service_category=self.service.category,
                status="down",
                latency_ms=0.0,
                message="Missing target URL in configuration",
            )

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.service.timeout,
                headers=self.service.headers,
            ) as client:
                response = await client.get(url)
                latency_ms = (time.perf_counter() - start_time) * 1000

                status: CheckStatus = (
                    "operational"
                    if response.status_code == self.service.expected_status
                    else ("degraded" if response.status_code < 500 else "down")
                )

                message = (
                    f"HTTP {response.status_code}"
                    if status == "operational"
                    else (
                        f"Expected {self.service.expected_status}, "
                        f"got {response.status_code}"
                    )
                )

                return CheckResult(
                    service_id=self.service.id,
                    service_name=self.service.name,
                    service_category=self.service.category,
                    status=status,
                    latency_ms=round(latency_ms, 2),
                    status_code=response.status_code,
                    message=message,
                )
        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                service_id=self.service.id,
                service_name=self.service.name,
                service_category=self.service.category,
                status="down",
                latency_ms=round(latency_ms, 2),
                message=f"Request timed out after {self.service.timeout}s",
            )
        except httpx.RequestError as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return CheckResult(
                service_id=self.service.id,
                service_name=self.service.name,
                service_category=self.service.category,
                status="down",
                latency_ms=round(latency_ms, 2),
                message=f"Connection error: {exc.__class__.__name__}",
            )
