"""Shim для clear – реализация переехала в release_tool.stages.clear"""
from release_tool.stages.clear import *  # type: ignore  # noqa: F401,F403

if __name__ == "__main__":
    from release_tool.stages.clear import run  # type: ignore
    run() 