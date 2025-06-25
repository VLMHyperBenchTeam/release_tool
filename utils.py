from __future__ import annotations

"""Вспомогательные утилиты общего назначения для release_tool."""

__all__ = ["substitute_placeholders"]


def substitute_placeholders(text: str, *, version: str, prev_version: str) -> str:
    """Подставляет плейсхолдеры {VERSION} и {PREV_VERSION}.

    Оставляет строку без изменений, если плейсхолдеры отсутствуют.
    """
    return text.replace("{VERSION}", version).replace("{PREV_VERSION}", prev_version) 