from importlib import import_module as _imp
import sys

# Упрощаем «star import»
_stages = _imp("release_tool.stages")

# ---------------------------------------------------------------------------
# Динамический реэкспорт core-модулей
# ---------------------------------------------------------------------------
for _m in (
    "config",
    "git",
    "git_utils",
    "git_helpers",
    "packages",
    "status_analyzer",
    "utils",
):
    _mod_full = f"release_tool.core.{_m}"
    _mod = _imp(_mod_full)
    sys.modules[f"release_tool.{_m}"] = _mod

__all__ = ["core", "stages"]
__all__ += [
    "config",
    "git",
    "git_utils",
    "git_helpers",
    "packages",
    "status_analyzer",
    "utils",
] 