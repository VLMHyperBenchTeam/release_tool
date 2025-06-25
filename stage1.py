"""Shim для обратной совместимости Stage1.
Реальная логика теперь в release_tool.stages.stage1
"""
from release_tool.stages.stage1 import *  # type: ignore

if __name__ == "__main__":
    from release_tool.stages.stage1 import run  # type: ignore
    run() 