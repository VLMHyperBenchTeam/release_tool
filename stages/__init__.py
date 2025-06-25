"""Подпакет со стадиями release_tool.

Пока оригинальная реализация стадий остаётся в корне пакета, но мы
публикуем их здесь через динамический реэкспорт. Благодаря этому можно
уже писать:

    from release_tool.stages.stage1 import run

и со временем перенести файлы физически без поломки API.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Final, Iterable

_STAGE_NAMES: Final[Iterable[str]] = (
    "stage0",
    "stage1",
    "stage2",
    "stage3",
    "stage4",
    "stage5",
    "stage6",
    "clear",
)

_current_pkg = __name__  # release_tool.stages

for _name in _STAGE_NAMES:
    _full_old = f"release_tool.{_name}"
    _mod: ModuleType = importlib.import_module(_full_old)
    # Регистрируем под новым путём — так import видит обе версии
    sys.modules[f"{_current_pkg}.{_name}"] = _mod
    # Добавляем в namespace пакета для from-import
    globals()[_name] = _mod  # type: ignore[assignment]

__all__ = list(_STAGE_NAMES) 