"""Shim для Stage2 – реализация переехала в release_tool.stages.stage2"""
from release_tool.stages.stage2 import *  # type: ignore

if __name__ == "__main__":
    from release_tool.stages.stage2 import run  # type: ignore
    run() 