"""
Mineral AI Tracker - Shared pytest fixtures (Sprint 11)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub optional runtime dependencies that are not installed in the test env
# ---------------------------------------------------------------------------

if "redis" not in sys.modules:
    _redis_stub = MagicMock()
    _redis_stub.Redis = MagicMock
    _redis_stub.StrictRedis = MagicMock
    _redis_stub.ConnectionError = ConnectionError
    sys.modules["redis"] = _redis_stub

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def load_fixture(filename: str) -> dict:
    return json.loads((FIXTURES_DIR / filename).read_text())


@pytest.fixture
def phi3_raw_output() -> dict:
    return load_fixture("phi3_raw_output.json")


@pytest.fixture
def claude_perfect_response() -> dict:
    return load_fixture("claude_perfect_response.json")


@pytest.fixture
def claude_corrupt_response() -> dict:
    return load_fixture("claude_corrupt_response.json")


# ---------------------------------------------------------------------------
# Database mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_conn():
    """
    A MagicMock that mimics a psycopg2 connection.
    cursor() returns a context-managed MagicMock cursor.
    """
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn


# ---------------------------------------------------------------------------
# Claude client mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_claude_perfect(claude_perfect_response):
    """Patch ClaudeClient.generate to return the perfect fixture."""
    with patch("ml.claude_client.ClaudeClient.generate", new_callable=AsyncMock) as mock:
        mock.return_value = {"text": json.dumps(claude_perfect_response)}
        yield mock


@pytest.fixture
def mock_claude_corrupt(claude_corrupt_response):
    """Patch ClaudeClient.generate to return the corrupt fixture."""
    with patch("ml.claude_client.ClaudeClient.generate", new_callable=AsyncMock) as mock:
        mock.return_value = {"text": json.dumps(claude_corrupt_response)}
        yield mock


# ---------------------------------------------------------------------------
# Quant provider mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_quant_provider_high():
    """MockQuantProvider with high coverage (AVN.V → 0.80, triggers discount)."""
    from engines.quant_provider import MockQuantProvider
    return MockQuantProvider()


@pytest.fixture
def mock_quant_provider_zero():
    """MockQuantProvider with zero coverage (URM.CN → 0.00)."""
    from engines.quant_provider import MockQuantProvider
    return MockQuantProvider()
