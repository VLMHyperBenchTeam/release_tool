"""Core API подмодуль release_tool.core.

Содержит высокоуровневые фасады и утилиты, которые могут использоваться
стадиями и внешними скриптами. Постепенно сюда будут переноситься модули
из корня пакета.
"""

from __future__ import annotations

# Переэкспорт существующих реализаций, пока они ещё находятся в корне
from ..config import Config, load_config  # noqa: F401
from ..git import GitRepo  # noqa: F401
from ..packages import Package, iter_release_packages  # noqa: F401

__all__ = [
    "Config",
    "load_config",
    "GitRepo",
    "Package",
    "iter_release_packages",
] 