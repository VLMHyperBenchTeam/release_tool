from importlib import import_module as _imp

# Упрощаем «star import»
_stages = _imp("release_tool.stages")

__all__ = ["core", "stages"] 