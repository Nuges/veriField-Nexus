"""Explicit DNS fixtures for local EO tests; no provider requests are made."""
import socket

import pytest

from app.domains.earth_observation.providers.stac_client import ALLOWED_COG_HOSTS


@pytest.fixture
def satellite_public_dns(monkeypatch):
    def resolve(host, port, *args, **kwargs):
        assert host in ALLOWED_COG_HOSTS, "Unexpected DNS lookup in satellite fixture"
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", int(port)))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
