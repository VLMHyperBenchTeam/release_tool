from __future__ import annotations

"""Общие helpers для работы с пакетами workspace.

Задача 2.1 roadmap: единая точка, где строятся пути к пакетам,
каталогам изменений и pyproject.toml.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# ----------------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------------


@dataclass(slots=True)
class Package:
    """Информация о пакете внутри workspace."""

    name: str
    path: Path
    changes_dir: Path
    pyproject: Path

    # невиртуальное свойство – удобно для `print(pkg)`
    def __str__(self) -> str:  # noqa: D401
        return f"<Package {self.name} at {self.path}>"


# ----------------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------------


def iter_release_packages(cfg: dict, *, include_all: bool = True) -> Iterator[Package]:
    """Итерирует пакеты workspace.

    Если *include_all* == False – возвращает только те пакеты, у которых
    существует каталог изменений (текущий релиз).
    """

    root = Path.cwd()
    packages_dir = root / cfg.get("packages_dir", "packages")
    if not packages_dir.is_dir():
        return  # пустой итератор

    changes_root = root / cfg.get("changes_output_dir", "release_tool/changes")

    for pkg_path in sorted(packages_dir.iterdir()):
        if not pkg_path.is_dir():
            continue

        if not include_all and not (changes_root / pkg_path.name).exists():
            # пакет не участвует в релизе – пропускаем
            continue

        yield Package(
            name=pkg_path.name,
            path=pkg_path,
            changes_dir=changes_root / pkg_path.name,
            pyproject=pkg_path / "pyproject.toml",
        ) 