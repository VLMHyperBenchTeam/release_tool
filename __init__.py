import importlib as _importlib
import sys

# ---------------------------------------------------------------------------
# Динамический реэкспорт core-модулей (должен быть ДО импорта stages)
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
    _mod = _importlib.import_module(_mod_full)
    sys.modules[f"release_tool.{_m}"] = _mod

# Упрощаем «star import» для стадий
_stages = _importlib.import_module("release_tool.stages")

__all__ = [
    "core",
    "stages",
    "config",
    "git",
    "git_utils",
    "git_helpers",
    "packages",
    "status_analyzer",
    "utils",
] 