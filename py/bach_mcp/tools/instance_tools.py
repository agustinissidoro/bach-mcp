"""
instance_tools.py
-----------------
A Claude written to directly (Claude Desktop, Claude Code) has no prompt line,
so it does not know which instance it is working for: the products go to the
active instance (session.py), named as always. These two tools let it look and
choose. Both are cheap: a few words in, a few lines out.

    get_instances            asks Max (server get_instances -> instances <name> <type> ...),
                             else answers with the last map the patch sent
    set_active_instance      the instance the other tools work for from now on

Not part of any mode (prompt/modes.py): an instance's own conversation is
already for that instance.
"""

from __future__ import annotations

from typing import Dict

from mcp.server.fastmcp import FastMCP

from .session import NoTarget, instances

INSTANCE_TOOLS = ("get_instances", "set_active_instance")


def describe(names: Dict[str, str], active: str) -> str:
    """`active: <name> (<type>)` and one `<name> <type>` per instance."""
    if not names:
        return "no instances: the patch has sent none"
    head = f"active: {active} ({names[active]})" if active in names else "active: none"
    return "\n".join([head, *(f"{name} {instance_type}" for name, instance_type in names.items())])


def register_instance_tools(mcp: FastMCP) -> None:
    """Register get_instances and set_active_instance on `mcp`; the hub answers them (session.py)."""

    @mcp.tool()
    def get_instances() -> str:
        """The instances in the Max patch, `<name> <type>` each, and the active one: the one your
        other tools work for."""
        try:
            hub = instances()
        except NoTarget as exc:
            return f"ERROR: {exc}"
        answered = hub.ask_instances()
        text = describe(*hub.instance_map())
        return text if answered else text + "\n(Max did not answer: the last map it sent)"

    @mcp.tool()
    def set_active_instance(name: str) -> str:
        """Choose the instance your other tools work for (see get_instances)."""
        try:
            hub = instances()
        except NoTarget as exc:
            return f"ERROR: {exc}"
        refusal = hub.choose(name)
        if refusal and hub.ask_instances():  # maybe it is new in the patch
            refusal = hub.choose(name)
        if refusal:
            return f"ERROR: {refusal}\n{describe(*hub.instance_map())}"
        names, active = hub.instance_map()
        return f"active: {active} ({names[active]})"


__all__ = ["INSTANCE_TOOLS", "register_instance_tools", "describe"]
