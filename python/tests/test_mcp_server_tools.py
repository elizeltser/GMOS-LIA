"""
Tests for mcp_server.server's tool response-shape contract.

FastMCP's @mcp.tool() decorator registers but returns the original callable,
so these can be called directly against a session with fake instruments
injected, without spinning up a real MCP client/stdio transport.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

import mcp_server.server as server


class _FakeLIA:
    def __init__(self, offset=1.0):
        self._offset = offset

    def set_offset(self, value):
        self._offset = value

    def get_offset(self):
        return self._offset


def test_set_offset_tool_returns_ok_true_on_success():
    server._session = None
    session = server._get_session()
    session._lia = _FakeLIA()
    result = server.set_offset(0.95)
    assert result["ok"] is True
    assert result["offset_v"] == 0.95


def test_set_offset_tool_returns_structured_error_out_of_range():
    server._session = None
    session = server._get_session()
    session._lia = _FakeLIA()
    result = server.set_offset(5.0)
    assert result["ok"] is False
    assert result["error_code"] == "out_of_range"
    assert "error" in result


def test_read_drain_state_tool_reports_internal_error_for_bad_channel():
    # Inject fakes so open_instruments() short-circuits without touching real
    # hardware; an invalid channel name raises a plain ValueError inside the
    # session, which the tool wrapper must still surface as a structured
    # error rather than letting it propagate.
    server._session = None
    session = server._get_session()
    session._lia = _FakeLIA()
    session._scu1 = object()
    session._scu2 = object()
    result = server.read_drain_state("SCU3")
    assert result["ok"] is False
    assert result["error_code"] == "internal_error"
    assert "error" in result
