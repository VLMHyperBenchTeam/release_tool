"""Shim для Stage3 – реализация переехала в release_tool.stages.stage3"""
from release_tool.stages.stage3 import *  # type: ignore  # noqa: F401,F403

if __name__ == "__main__":
    from release_tool.stages.stage3 import run  # type: ignore
    run() 