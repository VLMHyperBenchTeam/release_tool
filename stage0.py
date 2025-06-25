"""Shim для обратной совместимости Stage0 (перенесён в stages).
"""
from release_tool.stages.stage0 import *  # type: ignore

if __name__ == "__main__":
    from release_tool.stages.stage0 import run  # type: ignore
    run() 