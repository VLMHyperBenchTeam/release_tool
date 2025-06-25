from __future__ import annotations

"""Stage 0: подготавливает dev-ветки в пакетах перед началом релизного цикла.

Запуск:
    uv run release-tool-stage0 [--branch dev_branch] [--base-branch main] [--push] [--dry-run]

Действия по каждому пакету (при наличии каталога изменений):
1. `git fetch <remote>` (по умолчанию origin).
2. `git checkout -B <branch> <remote>/<base_branch>` — создаём/обновляем dev-ветку
   от актуальной <base_branch>.
3. (опц.) `git push --set-upstream <remote> <branch>` — если указан --push.

Это автоматизирует шаг, который раньше выполнялся вручную перед Stage 2/3/4.
"""

import argparse
import pathlib
import sys

from .config import load_config
from .git_utils import _run_git, _push_repo


def _process_package(pkg: pathlib.Path, branch: str, base: str, remote: str, push: bool, dry_run: bool) -> None:
    if dry_run:
        print(f"[stage0]   [dry-run] git -C {pkg} fetch {remote}")
        print(f"[stage0]   [dry-run] git -C {pkg} checkout -B {branch} {remote}/{base}")
        if push:
            print(f"[stage0]   [dry-run] git -C {pkg} push --set-upstream {remote} {branch}")
        return

    _run_git(pkg, ["fetch", remote], capture=False)
    # checkout / recreate branch from remote base
    proc = _run_git(pkg, ["checkout", "-B", branch, f"{remote}/{base}"], capture=False)
    if proc.returncode != 0:
        # fallback: if remote branch missing, create from local base
        _run_git(pkg, ["checkout", "-B", branch, base], capture=False)

    if push:
        _push_repo(pkg, remote)
        print(f"[stage0]   🚀 ветка {branch} отправлена")

    print(f"[stage0]   ✅ {pkg.name}: подготовлена ветка {branch} (от {base})")


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 0: prepare dev branches from base branch")
    parser.add_argument("--branch", default="dev_branch", help="Имя dev-ветки")
    parser.add_argument("--base-branch", default="main", help="Базовая ветка, от которой создаётся dev-ветка")
    parser.add_argument("--push", action="store_true", help="Отправить ветку в origin после создания")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage0] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    remote_name = cfg.get("git_remote", "origin")

    # Фильтруем пакеты по наличию каталога изменений (как Stage5/6)
    changes_root = root / cfg.get("changes_output_dir", "release_tool/changes")

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        if not (changes_root / pkg.name).exists():
            # пакет не участвует в текущем релизе
            continue
        print(f"[stage0] Обрабатываем пакет: {pkg.name}")
        _process_package(pkg, args.branch, args.base_branch, remote_name, args.push, dry_run=args.dry_run or cfg.get("dry_run", False))
        processed += 1

    print(f"[stage0] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run() 