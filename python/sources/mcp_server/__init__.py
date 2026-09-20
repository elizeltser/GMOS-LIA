"""
MCP server package: interactive operating-point search for GMOS transistors.

Exposes ``OperatingPointSession`` (persistent instrument handles + validated
setpoint/readout methods) and the MCP tool server in ``server.py`` that wraps
it for a Claude Code co-worker.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .operating_point_session import OperatingPointSession

__all__ = ["OperatingPointSession"]


def __getattr__(name):
    # Lazy: setups.lia_setup imports mcp_server.errors, so importing the
    # session eagerly here would be circular (session imports setups.lia_setup).
    if name == "OperatingPointSession":
        from .operating_point_session import OperatingPointSession

        return OperatingPointSession
    raise AttributeError(name)
