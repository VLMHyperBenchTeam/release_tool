# deprecated shim ─ переехал в release_tool.core.config
from release_tool.core.config import *  # type: ignore F401,F403

if __name__ == "__main__":
    from release_tool.core.config import load_config as _run
    _run() 