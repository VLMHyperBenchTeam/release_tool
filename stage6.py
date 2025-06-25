"""Shim для Stage6 – реализация переехала в release_tool.stages.stage6"""
from release_tool.stages.stage6 import *  # type: ignore  # noqa: F401,F403

if __name__ == "__main__":
    from release_tool.stages.stage6 import run  # type: ignore
    run() 