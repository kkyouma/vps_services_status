"""Base abstractions for health-check probes."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

CheckStatus = Literal["operational", "degraded", "down"]


class CheckResult(BaseModel):
    """Result of a single probe check."""

    service_id: str
    service_name: str
    service_category: str = "VPS Services"
    status: CheckStatus
    latency_ms: float
    status_code: int | None = None
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseProbe(ABC):
    """Abstract base class for all probes."""

    @abstractmethod
    async def check(self) -> CheckResult:
        """Execute the probe and return the CheckResult."""
        pass
