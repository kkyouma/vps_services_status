"""Probe factory and registry."""

from state_panel.config import ServiceConfig
from state_panel.probes.base import BaseProbe
from state_panel.probes.http_probe import HttpProbe
from state_panel.probes.tcp_probe import TcpProbe


def get_probe(service: ServiceConfig) -> BaseProbe:
    """Create a probe instance for a given service configuration."""
    if service.type == "http":
        return HttpProbe(service)
    if service.type == "tcp":
        return TcpProbe(service)
    raise ValueError(f"Unsupported probe type: {service.type}")
