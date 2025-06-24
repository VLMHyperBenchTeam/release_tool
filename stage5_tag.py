from __future__ import annotations

"""Stage 5: ставит аннотированный тег на release-коммит.

Предполагается, что скрипт запускается *внутри CI* после мержа PR с release-коммитом
в ветку `main`.

Запуск:
    python -m release_tool.stage5_tag [--push] [--dry-run]
"""

import argparse
import pathlib
import re
import sys
from typing import Optional

from .config import load_config
from .git_utils import _run_git, GitError


def _get_package_version(pyproject: pathlib.Path) -> str:
    pattern = re.compile(r"^\s*version\s*=\s*\"(?P<v>[^\"]+)\"")
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            return m.group("v")
    raise RuntimeError("version field not found")


def _tag_exists(repo: pathlib.Path, tag: str) -> bool:
    proc = _run_git(repo, ["tag", "-l", tag])
    return bool(proc.stdout.strip())


def _create_tag(repo: pathlib.Path, tag: str, message: str, push: bool, dry_run: bool) -> None:
    if dry_run:
        print(f"[stage5]   [dry-run] git -C {repo} tag -a {tag} -m \"{message.splitlines()[0]}…\"")
        if push:
            print(f"[stage5]   [dry-run] git -C {repo} push origin {tag}")
        return
    proc = _run_git(repo, ["tag", "-a", tag, "-m", message], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    if push:
        proc = _run_git(repo, ["push", "origin", tag], capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr)


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 5: create and push annotated tag")
    parser.add_argument("--push", action="store_true", help="git push тег после создания")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage5] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        pyproject = pkg / "pyproject.toml"
        if not pyproject.exists():
            continue
        version = _get_package_version(pyproject)
        tag_name = f"{cfg.get('tag_prefix', '')}{version}"
        print(f"[stage5] Обрабатываем пакет: {pkg.name} → {tag_name}")
        if _tag_exists(pkg, tag_name):
            print(f"[stage5]   🟡 тег уже существует, пропускаем")
            continue
        # Считываем сообщение последнего коммита (release-commit)
        proc = _run_git(pkg, ["log", "-1", "--pretty=%B"])
        commit_msg = proc.stdout.strip() or f"Release {tag_name}"
        _create_tag(pkg, tag_name, commit_msg, push=args.push, dry_run=args.dry_run or cfg.get("dry_run", False))
        print(f"[stage5]   ✅ тег создан")
        processed += 1

    print(f"[stage5] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run() 