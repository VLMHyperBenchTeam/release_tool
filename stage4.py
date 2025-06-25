"""Shim для Stage4 – реализация переехала в release_tool.stages.stage4"""
from release_tool.stages.stage4 import *  # type: ignore  # noqa: F401,F403

if __name__ == "__main__":
    from release_tool.stages.stage4 import run  # type: ignore
    run() 