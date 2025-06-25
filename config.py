"""Загрузка конфигурации release_tool (roadmap 2.3).

Теперь используется класс `Config` с дефолтными значениями.
Источник ищется в следующем порядке:

1. ``release_tool.toml`` в корне workspace;
2. ``release_tool/release_tool.toml`` (рядом с submodule);
3. ``pyproject.toml`` секция ``[tool.release_tool]``;
4. Встроенный ``release_tool.toml`` рядом с модулем (fallback).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any, Iterator

import tomlkit  # type: ignore  # third-party

# ---------------------------------------------------------------------------
# Config dataclass-like Mapping
# ---------------------------------------------------------------------------


class Config(dict):  # pylint: disable=too-many-ancestors
    """Словарь-обёртка с дефолтами и парсингом TOML.

    Наследуемся от ``dict`` ради обратной совместимости: все стадии уже
    используют ``cfg["key"]`` и ``cfg.get()``. При этом внутрь добавляем
    удобные свойства и метаданные.
    """

    _DEFAULTS: dict[str, Any] = {
        "packages_dir": "packages",
        "changes_output_dir": "release_tool/changes",
        "changes_uncommitted_filename": "changes_uncommitted.txt",
        "changes_since_tag_filename": "changes_since_tag.txt",
        "tag_message_filename": "tag_message.txt",
        "staging_pyproject_path": "staging/pyproject.toml",
        "prod_pyproject_path": "prod/pyproject.toml",
        # служебное
        "dry_run": False,
    }

    # --- construction --------------------------------------------------

    def __init__(self, data: dict[str, Any] | None = None, *, source: str = "<default>") -> None:  # noqa: D401
        merged = dict(self._DEFAULTS)
        if data:
            merged.update(data)
        super().__init__(merged)
        self["_config_source"] = source

    # --- convenience accessors ----------------------------------------

    def __getattr__(self, item: str) -> Any:  # noqa: D401
        try:
            return self[item]
        except KeyError as exc:  # pragma: no cover – для mypy
            raise AttributeError(item) from exc

    # typing helpers
    def __getitem__(self, key: str) -> Any:  # type: ignore[override]
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return super().get(key, default)

    # --- dump / representation ----------------------------------------

    def __repr__(self) -> str:  # noqa: D401
        return f"<Config {dict(self)!r} from {self['_config_source']}>"

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @classmethod
    def _iter_candidate_files(cls) -> Iterator[pathlib.Path]:
        root = pathlib.Path.cwd()
        yield root / "release_tool.toml"
        yield root / "release_tool" / "release_tool.toml"
        yield root / "pyproject.toml"
        yield pathlib.Path(__file__).resolve().parent / "release_tool.toml"  # fallback bundled

    @classmethod
    def _parse_toml(cls, path: pathlib.Path) -> dict[str, Any]:
        """Читает файл TOML и возвращает секцию tool.release_tool (или весь TOML)."""
        raw_text = path.read_text(encoding="utf-8")
        data: Any = tomlkit.parse(raw_text)

        # Если это pyproject.toml, нужная секция внутри tool.*
        if path.name == "pyproject.toml":
            try:
                return data["tool"]["release_tool"]  # type: ignore[index]
            except KeyError:
                return {}
        # иначе это standalone release_tool.toml – ожидаем верхний уровень
        return data.get("tool", {}).get("release_tool", data)  # support both

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, config_path: str | pathlib.Path | None = None) -> "Config":  # noqa: D401
        """Загружает конфиг из указанного пути или ищет кандидатов."""

        if config_path is not None:
            path = pathlib.Path(config_path)
            if not path.exists():
                print(f"[release_tool] Конфигурационный файл не найден: {path}", file=sys.stderr)
                raise SystemExit(1)
            data = cls._parse_toml(path)
            return cls(data, source=str(path.relative_to(pathlib.Path.cwd())))

        # auto-discovery
        for candidate in cls._iter_candidate_files():
            if candidate.exists():
                data = cls._parse_toml(candidate)
                return cls(data, source=str(candidate.relative_to(pathlib.Path.cwd())))

        # ни одного файла – возвращаем конфиг по умолчанию
        print("[release_tool] Конфигурационный файл не найден – используются значения по умолчанию", file=sys.stderr)
        return cls()


# ---------------------------------------------------------------------------
# Backward-compat wrappers – чтобы не менять импорты во всех стадиях
# ---------------------------------------------------------------------------


def load_config(config_path: pathlib.Path | str | None = None) -> Config:  # noqa: D401
    """Совместимая обёртка поверх ``Config.load``."""

    return Config.load(config_path) 