"""Temporary alias: both Ping entrypoints now use PingTool."""


def run():
    from Program.registry import registry
    from Program.ui import run_tool
    return run_tool(registry.get("ping"), pause_after=False)
