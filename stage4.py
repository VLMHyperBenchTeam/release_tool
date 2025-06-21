"""Stage 4: bump версии, создаёт тег и (опц.) пушит.

Запуск:
    python -m release_tool.stage4 [--dry-run] [--bump patch|minor|major|dev] [--push]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Optional

from packaging.version import Version, InvalidVersion  # type: ignore

from .config import load_config
from .git_utils import commit_and_tag, _run_git, GitError

# regexes
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
    m = _SEMVER_RE.match(version_str)
    if not m:
        raise ValueError("not semver")
    major, minor, patch = map(int, (m.group("major"), m.group("minor"), m.group("patch")))
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


def update_version_in_pyproject(pyproject: pathlib.Path, new_version: str) -> None:
    lines = pyproject.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("version") and "=" in line:
            lines[i] = f"version = \"{new_version}\""
            break
    else:
        raise RuntimeError("version field not found")
    pyproject.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_package(pkg_path: pathlib.Path, cfg: dict, bump_part: str, push: bool, dry_run: bool = False) -> None:
    root = pathlib.Path.cwd()
    changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    tag_msg_file = changes_dir / cfg["tag_message_filename"]
    if not tag_msg_file.exists():
        print(f"[stage4]   {pkg_path.name}: файл tag-сообщения не найден")
        return
    tag_message = tag_msg_file.read_text(encoding="utf-8").strip()
    if not tag_message:
        print(f"[stage4]   {pkg_path.name}: пустое tag-сообщение")
        return

    pyproject = pkg_path / "pyproject.toml"
    if not pyproject.exists():
        print(f"[stage4]   {pkg_path.name}: pyproject.toml не найден")
        return
    current_version = None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version") and "=" in line:
            current_version = line.split("=", 1)[1].strip().strip("\"'")
            break
    if current_version is None:
        print(f"[stage4]   {pkg_path.name}: версия не найдена в pyproject.toml")
        return

    new_version = bump_version(current_version, bump_part)

    if dry_run:
        print(f"[stage4]   [dry-run] {pkg_path.name}: {current_version} -> {new_version}")
    else:
        print(f"[stage4]   📦 {pkg_path.name}: {current_version} -> {new_version}")
        update_version_in_pyproject(pyproject, new_version)

    # add -A
    if dry_run:
        print(f"[stage4]   [dry-run] git -C {pkg_path} add -A")
    else:
        proc = _run_git(pkg_path, ["add", "-A"], capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr)

    tag_name = f"{cfg['tag_prefix']}{new_version}"
    commit_and_tag(
        pkg_path,
        tag_message,
        tag_name,
        remote=cfg.get("git_remote", "origin"),
        dry_run=dry_run,
    )

    if push and not dry_run:
        # Commit_and_tag already pushes; additional push not needed.
        pass

    print(f"[stage4]   ✅ {pkg_path.name}: версия {new_version} выпущена{' и отправлена' if push else ''}")


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 4: bump version & tag")
    parser.add_argument("--bump", choices=["patch", "minor", "major", "dev"], default="dev")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    action = f"bump версий ({args.bump})" + (" и push" if args.push else "")
    print(f"[stage4] Выполняем {action} для пакетов с подготовленными tag-сообщениями...")
    
    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage4] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        print(f"[stage4] Проверяем пакет: {pkg.name}")
        process_package(pkg, cfg, bump_part=args.bump, push=args.push, dry_run=args.dry_run or cfg.get("dry_run", False))
        # Проверяем, был ли пакет обработан
        changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg.name
        tag_msg_file = changes_dir / cfg["tag_message_filename"]
        if tag_msg_file.exists() and tag_msg_file.read_text(encoding="utf-8").strip():
            processed += 1
    
    if processed == 0:
        print("[stage4] ✅ Нет пакетов с подготовленными tag-сообщениями")
    else:
        print(f"[stage4] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run() 