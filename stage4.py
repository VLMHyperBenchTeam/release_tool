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
from .git_utils import commit_and_tag, _run_git, GitError, get_last_tag

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
    """Повышает *release*-часть версии, игнорируя суффиксы (например, .devN).

    При bump-е *patch/minor/major* суффикс (.devN, .rc, и др.) отбрасывается, т.е.
    строка ``0.0.1.dev3`` с ``part="patch"`` превратится в ``0.0.2``.

    Основано на ``packaging.version.Version``: она корректно парсит PEP 440-совместимые
    версии (в т. ч. c дев- и pre-релизами). Release-кортеж ``v.release`` всегда
    содержит от 1 до 3 чисел (major, minor, patch). Недостающие элементы
    дополняем нулями, чтобы гарантировать три компонента.
    """

    try:
        v = Version(version_str)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid version: {version_str}") from exc

    # ``v.release`` — tuple(int, …) длиной 1-3. Дополним до 3.
    release = list(v.release) + [0, 0]
    major, minor, patch = release[:3]

    # Если хотим выпустить текущий dev-релиз → просто убираем суффикс .devN
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


def update_version_in_pyproject(pyproject: pathlib.Path, new_version: str) -> None:
    lines = pyproject.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("version") and "=" in line:
            lines[i] = f"version = \"{new_version}\""
            break
    else:
        raise RuntimeError("version field not found")
    pyproject.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clean_workspace_sources(pyproject: pathlib.Path, dry_run: bool = False) -> bool:
    """Удаляет строки внутри [tool.uv.sources] со ссылкой ``workspace = true``.

    Возвращает True, если файл был изменён.
    """

    original_lines = pyproject.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    in_sources_block = False
    changed = False

    for line in original_lines:
        stripped = line.lstrip()

        # Определяем вход/выход из секции [tool.uv.sources]
        if stripped.startswith("[tool.uv.sources]"):
            in_sources_block = True
            new_lines.append(line)
            continue

        if in_sources_block and stripped.startswith("[") and not stripped.startswith("[tool.uv.sources]"):
            # Вышли из блока источников
            in_sources_block = False

        if in_sources_block and "workspace" in stripped:
            # Пропускаем ссылки вида { workspace = true }
            changed = True
            continue  # не добавляем строку

        new_lines.append(line)

    if changed and not dry_run:
        pyproject.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return changed


def _update_tag_in_prod_pyproject(prod_pyproject: pathlib.Path, project_name: str, tag_name: str, dry_run: bool = False) -> bool:
    """Меняет значение ``tag = "…"`` для указанного пакета в prod/pyproject.toml.

    Parameters
    ----------
    prod_pyproject : pathlib.Path
        Путь к prod/pyproject.toml.
    project_name : str
        Имя пакета так, как оно встречается в строке источников (например, "bench-utils").
    tag_name : str
        Новый тег (например, "v1.2.3").
    dry_run : bool, default False
        Если True, файл не изменяется, а возвращается, было бы ли изменение.

    Returns
    -------
    bool
        True, если файл был изменён.
    """

    if not prod_pyproject.exists():
        # Нет prod-конфигурации – просто пропускаем
        return False

    pattern = re.compile(rf"^(\s*{re.escape(project_name)}\s*=.*?tag\s*=\s*\")([^\"]+)(\")(.+)$")
    changed = False
    new_lines: list[str] = []
    for line in prod_pyproject.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            old_tag = m.group(2)
            if old_tag != tag_name:
                changed = True
                line = f"{m.group(1)}{tag_name}{m.group(3)}{m.group(4)}"
        new_lines.append(line)

    if changed and not dry_run:
        prod_pyproject.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return changed


def bump_package(pkg_path: pathlib.Path, cfg: dict, bump_part: str, dry_run: bool = False) -> None:
    root = pathlib.Path.cwd()
    changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    tag_msg_file = changes_dir / cfg["tag_message_filename"]
    if not tag_msg_file.exists():
        print(f"[stage4]   {pkg_path.name}: файл tag-сообщения не найден")
        return
    raw_tag_message = tag_msg_file.read_text(encoding="utf-8").strip()
    if not raw_tag_message:
        print(f"[stage4]   {pkg_path.name}: пустое tag-сообщение")
        return

    pyproject = pkg_path / "pyproject.toml"
    if not pyproject.exists():
        print(f"[stage4]   {pkg_path.name}: pyproject.toml не найден")
        return
    current_version = None
    project_name = None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version") and "=" in stripped:
            current_version = line.split("=", 1)[1].strip().strip("\"'")
            break
        if stripped.startswith("name") and "=" in stripped and project_name is None:
            project_name = stripped.split("=", 1)[1].strip().strip("\"'")
    if current_version is None:
        print(f"[stage4]   {pkg_path.name}: версия не найдена в pyproject.toml")
        return
    if project_name is None:
        project_name = pkg_path.name.replace("_", "-")  # запасной вариант

    new_version = bump_version(current_version, bump_part)

    if dry_run:
        print(f"[stage4]   [dry-run] {pkg_path.name}: {current_version} -> {new_version}")
    else:
        print(f"[stage4]   📦 {pkg_path.name}: {current_version} -> {new_version}")
        update_version_in_pyproject(pyproject, new_version)

    # Удаляем workspace-ссылки для продового тега
    _clean_workspace_sources(pyproject, dry_run=dry_run)

    # add -A
    if dry_run:
        print(f"[stage4]   [dry-run] git -C {pkg_path} add -A")
    else:
        proc = _run_git(pkg_path, ["add", "-A"], capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr)

    # Определяем предыдущий релиз
    prev_tag = get_last_tag(pkg_path)
    prev_version: str | None = None
    if prev_tag:
        prefix = cfg.get("tag_prefix", "")
        if prefix and prev_tag.startswith(prefix):
            prev_version = prev_tag[len(prefix) :]
        else:
            prev_version = prev_tag

    tag_message = (
        raw_tag_message.replace("{VERSION}", new_version)
        .replace("{PREV_VERSION}", prev_version or "")
        .strip()
    )

    tag_name = f"{cfg['tag_prefix']}{new_version}"
    # Создаём временный «чистый» коммит: bump + удаление workspace
    commit_and_tag(
        pkg_path,
        tag_message,
        tag_name,
        remote=cfg.get("git_remote", "origin"),
        push=False,
        dry_run=dry_run,
    )

    # Сохраняем исходный HEAD до любых изменений
    orig_head = _run_git(pkg_path, ["rev-parse", "HEAD"], capture=True).stdout.strip()

    if not dry_run:
        # --------------------------------------------------
        # Post-release: начинаем новый dev-цикл прямо в той же ветке
        #   * для обычных релизов (patch/minor/major) — X.Y.(Z+1).dev0
        #   * для dev-релизов bump делать не нужно
        # --------------------------------------------------

        next_dev: str | None = None
        if bump_part != "dev":
            # Восстанавливаем pyproject из исходного коммита (с workspace-ссылками)
            _run_git(
                pkg_path,
                ["checkout", orig_head, "--", str(pyproject.relative_to(pkg_path))],
                capture=False,
            )

            next_dev = _next_dev_version(new_version)
            update_version_in_pyproject(pyproject, next_dev)
            _run_git(pkg_path, ["add", str(pyproject.relative_to(pkg_path))], capture=False)
            _run_git(
                pkg_path,
                [
                    "commit",
                    "-m",
                    f"chore: start {next_dev} development",
                ],
                capture=False,
            )

        # Обновляем prod/pyproject.toml
        prod_py_path = root / cfg.get("prod_pyproject_path", "prod/pyproject.toml")
        if _update_tag_in_prod_pyproject(prod_py_path, project_name, tag_name, dry_run=dry_run):
            print(f"[stage4]   📝 prod/pyproject.toml: обновлён тег для {project_name} → {tag_name}")

        if next_dev is not None:
            print(f"[stage4]   ✅ {pkg_path.name}: версия {new_version} выпущена; начат dev-цикл {next_dev}")
        else:
            print(f"[stage4]   ✅ {pkg_path.name}: версия {new_version} выпущена")


def push_package(pkg_path: pathlib.Path, cfg: dict, dry_run: bool = False) -> None:
    """Отправляет коммиты и теги в удалённый репозиторий."""

    remote = cfg.get("git_remote", "origin")
    if dry_run:
        print(f"[stage4]   [dry-run] git -C {pkg_path} push {remote}")
        print(f"[stage4]   [dry-run] git -C {pkg_path} push {remote} --tags")
        return

    # Сначала отправляем ветку (fast-forward до dev-коммита), затем теги
    for cmd in [["push", remote], ["push", remote, "--tags"]]:
        proc = _run_git(pkg_path, cmd, capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr or f"git {' '.join(cmd)} failed in {pkg_path}")

    print(f"[stage4]   ✅ {pkg_path.name}: изменения отправлены")


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 4: bump версии и/или push изменений")
    parser.add_argument("--bump", choices=["patch", "minor", "major", "dev"], help="Какую часть версии увеличить")
    parser.add_argument("--push", action="store_true", help="Отправить подготовленные релизы в удалённый репозиторий")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    do_bump = args.bump is not None
    do_push = args.push

    if not (do_bump or do_push):
        parser.error("Нужно указать хотя бы --bump или --push")

    if do_bump and do_push:
        print(f"[stage4] Выполняем bump версий ({args.bump}) с последующим push...")
    elif do_bump:
        print(f"[stage4] Выполняем bump версий ({args.bump}) без push...")
    else:  # только push
        print(f"[stage4] Выполняем push подготовленных релизов без изменения версий...")
    
    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage4] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue

        # Каталог changes/<pkg>/ и файл tag_message нужны и для bump, и для push
        changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg.name
        tag_msg_file = changes_dir / cfg["tag_message_filename"]
        if not tag_msg_file.exists() or not tag_msg_file.read_text(encoding="utf-8").strip():
            continue

        print(f"[stage4] Обрабатываем пакет: {pkg.name}")
        # Сначала bump (если требуется), затем push (если требуется)
        if do_bump:
            bump_package(pkg, cfg, bump_part=args.bump, dry_run=args.dry_run or cfg.get("dry_run", False))
        if do_push:
            push_package(pkg, cfg, dry_run=args.dry_run or cfg.get("dry_run", False))
        processed += 1
    
    if processed == 0:
        print("[stage4] ✅ Нет пакетов для обработки")
    else:
        print(f"[stage4] ✅ Завершено. Обработано пакетов: {processed}")


def _next_dev_version(release_version: str) -> str:
    """Возвращает версию следующего dev-цикла после *release_version*.

    • Если *release_version* — **stable** (без суффикса .devN) → увеличиваем patch-часть на +1 и
      добавляем суффикс ``.dev0`` (``0.1.2`` → ``0.1.3.dev0``).
    • Если *release_version* уже содержит ``.devN`` → просто увеличиваем ``N``
      (``0.1.2.dev3`` → ``0.1.2.dev4``).
    """

    try:
        v = Version(release_version)
    except InvalidVersion as exc:  # pragma: no cover
        raise ValueError(f"Invalid release version: {release_version}") from exc

    # Если уже dev-релиз — инкрементируем dev-номер
    if v.dev is not None:
        return bump_dev(release_version)

    # Stable release: bump patch
    release = list(v.release) + [0, 0]
    major, minor, patch = release[:3]
    patch += 1
    return f"{major}.{minor}.{patch}.dev0"


if __name__ == "__main__":
    run() 