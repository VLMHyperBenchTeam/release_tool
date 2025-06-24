from __future__ import annotations

"""Stage 4 (prepare): делает *release*-коммит без тега.

Запуск:
    python -m release_tool.stage4_prepare [--bump patch|minor|major|dev] [--push] [--dry-run]

Алгоритм по пакету:
1. Читает release_tool/changes/<pkg>/tag_message.txt (должен быть заполнен).
2. Bump-ает версию (patch/minor/major/dev) в pyproject.toml.
3. Удаляет строки `workspace = true` из `[tool.uv.sources]` (чистый релиз).
4. `git add -A && git commit -m <tag_message>` (без тега!).
5. (опц.) push коммит.

После этого разработчик создаёт PR dev_branch → main.
"""

import argparse
import pathlib
import sys
from packaging.version import Version, InvalidVersion  # type: ignore
from typing import Optional
import re

from .config import load_config
from .git_utils import (
    _run_git,
    GitError,
    commit_all,  # для push если надо
    _push_repo,
)

_SEMVER_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
_DEV_RE = re.compile(r"^(?P<prefix>.*?)(?P<dev>\.dev(?P<num>\d+))?$")


def bump_dev(version_str: str) -> str:
    try:
        _ = Version(version_str)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid version: {version_str}") from exc
    m = _DEV_RE.match(version_str)
    if not m:
        raise ValueError("bad version")
    prefix = m.group("prefix")
    num = int(m.group("num") or 0) + 1
    return f"{prefix}.dev{num}"


def bump_semver(version_str: str, part: str) -> str:
    """Bump release part ignoring suffixes (.devN)"""

    try:
        v = Version(version_str)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid version: {version_str}") from exc

    release = list(v.release) + [0, 0]
    major, minor, patch = release[:3]

    # Если dev-версия → завершить текущий релиз без увеличения patch
    if v.dev is not None and part == "patch":
        return f"{major}.{minor}.{patch}"

    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = patch = 0
    else:
        raise ValueError("unknown part")

    return f"{major}.{minor}.{patch}"


def bump_version(version_str: str, part: str) -> str:
    if part == "dev":
        return bump_dev(version_str)
    return bump_semver(version_str, part)


def _clean_workspace_sources(pyproject: pathlib.Path, dry_run: bool = False) -> None:
    """Удаляет строки `workspace = true` из секции [tool.uv.sources]"""
    lines = pyproject.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    inside_sources = False
    changed = False
    for line in lines:
        if line.strip().startswith("[tool.uv.sources]"):
            inside_sources = True
            new_lines.append(line)
            continue
        if inside_sources:
            if line.strip().startswith("["):
                inside_sources = False
            elif "workspace" in line and "true" in line:
                changed = True
                continue  # skip
        new_lines.append(line)
    if changed and not dry_run:
        pyproject.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def update_version_in_pyproject(pyproject: pathlib.Path, new_version: str) -> None:
    lines = pyproject.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("version") and "=" in line:
            lines[i] = f"version = \"{new_version}\""
            break
    else:
        raise RuntimeError("version field not found")
    pyproject.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _process_package(pkg_path: pathlib.Path, cfg: dict, bump_part: str, push: bool, dry_run: bool) -> None:
    root = pathlib.Path.cwd()
    changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    tag_msg_file = changes_dir / cfg["tag_message_filename"]
    if not tag_msg_file.exists() or not tag_msg_file.read_text(encoding="utf-8").strip():
        print(f"[stage4]   {pkg_path.name}: файл tag-сообщения не найден или пуст")
        return
    tag_message = tag_msg_file.read_text(encoding="utf-8").strip()

    pyproject = pkg_path / "pyproject.toml"
    if not pyproject.exists():
        print(f"[stage4]   {pkg_path.name}: pyproject.toml не найден")
        return

    # current version
    current_version: Optional[str] = None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version") and "=" in line:
            current_version = line.split("=", 1)[1].strip().strip("\"'")
            break
    if current_version is None:
        print(f"[stage4]   {pkg_path.name}: версия не найдена")
        return

    new_version = bump_version(current_version, bump_part)

    if dry_run:
        print(f"[stage4]   [dry-run] {pkg_path.name}: {current_version} -> {new_version}")
        print(f"[stage4]   [dry-run] git -C {pkg_path} add -A")
        print(f"[stage4]   [dry-run] git -C {pkg_path} commit -m <tag_message>")
        return

    print(f"[stage4]   📦 {pkg_path.name}: {current_version} -> {new_version}")
    update_version_in_pyproject(pyproject, new_version)
    _clean_workspace_sources(pyproject)

    # commit
    proc = _run_git(pkg_path, ["add", "-A"], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    proc = _run_git(pkg_path, ["commit", "-m", tag_message], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    print(f"[stage4]   ✅ commit создан: {new_version}")

    if push:
        try:
            _push_repo(pkg_path, cfg.get("git_remote", "origin"))
            print(f"[stage4]   🚀 изменения отправлены")
        except Exception as exc:  # noqa: BLE001
            print(f"[stage4]   ❌ push error: {exc}")


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 4 (prepare release): commit without tag")
    parser.add_argument("--bump", required=True, choices=["patch", "minor", "major", "dev"], help="Какая часть версии")
    parser.add_argument("--push", action="store_true", help="Выполнить git push после коммита")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage4] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[stage4] Выполняем prepare-release bump ({args.bump})…")
    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        print(f"[stage4] Обрабатываем пакет: {pkg.name}")
        _process_package(pkg, cfg, args.bump, push=args.push, dry_run=args.dry_run or cfg.get("dry_run", False))
        processed += 1

    print(f"[stage4] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run() 