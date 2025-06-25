"""Shim для Stage5 – реализация переехала в release_tool.stages.stage5"""
from release_tool.stages.stage5 import *  # type: ignore  # noqa: F401,F403

if __name__ == "__main__":
    from release_tool.stages.stage5 import run  # type: ignore
    run() 