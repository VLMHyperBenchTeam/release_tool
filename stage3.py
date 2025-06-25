"""
Stage 3: собирает список коммитов и/или diff после указанного (или последнего) тега.

Создаёт `<changes_since_tag_filename>` внутри пакета.

Запуск:
    uv run release-tool-stage3 [--tag TAG_NAME] [--dry-run]
    # или
    uv run python -m release_tool.stage3 [--tag TAG_NAME] [--dry-run]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from .config import load_config
from .git_utils import (
    get_last_tag,
    get_log_since_tag,
    has_changes_since_last_tag,
    get_diff_since_tag,
    _run_git,
)


def _build_changes_text(
    commits_log: str,
    diff_text: str | None,
) -> str:
    """Формирует итоговый текст файла изменений.

    Если *diff_text* не *None*, то добавляется секция с diff.
    """

    # Возвращаем только diff без списка коммитов.
    if diff_text:
        return diff_text + "\n"
    return ""


def process_package(
    pkg_path: pathlib.Path,
    cfg: dict,
    dry_run: bool = False,
    include_diff: bool = False,
    from_tag: str | None = None,
) -> None:
    # Определяем тег, от которого собираем изменения
    if from_tag:
        # Проверяем, что указанный тег существует
        proc = _run_git(pkg_path, ["rev-parse", "--verify", from_tag], capture=True)
        if proc.returncode != 0:
            print(f"[stage3]   {pkg_path.name}: тег '{from_tag}' не найден")
            return
        tag_to_use = from_tag
    else:
        # Используем последний тег
        tag_to_use = get_last_tag(pkg_path)
        if not has_changes_since_last_tag(pkg_path):
            print(f"[stage3]   {pkg_path.name}: нет новых коммитов после последнего тега")
            return

    # Игнорируем лог коммитов — сохраняем только diff
    diff_txt = get_diff_since_tag(pkg_path, tag_to_use)
    log = ""

    if not log and not diff_txt:
        print(f"[stage3]   {pkg_path.name}: нет изменений для записи")
        return

    root = pathlib.Path.cwd()
    out_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    out_dir.mkdir(parents=True, exist_ok=True)
    changes_file = out_dir / cfg["changes_since_tag_filename"]
    if dry_run:
        print(f"[dry-run] would write changes to {changes_file}")
        preview = _build_changes_text(log, diff_txt)
        print(preview)
        return

    changes_file.write_text(_build_changes_text(log, diff_txt), encoding="utf-8")
    print(f"[stage3]   ✅ {pkg_path.name}: коммиты сохранены в {changes_file.relative_to(pathlib.Path.cwd())}")

    # Создаём пустой файл для tag-сообщения в том же каталоге
    tag_msg_file = out_dir / cfg["tag_message_filename"]
    if not tag_msg_file.exists():
        template = (
            "## Релиз {VERSION}\n\n"
            "_Изменения по сравнению с {PREV_VERSION}_\n\n"
            "<!-- Опишите основные изменения здесь -->\n"
        )
        if not dry_run:
            tag_msg_file.write_text(template, encoding="utf-8")
        print(
            f"[stage3]   📝 {pkg_path.name}: создан файл {tag_msg_file.relative_to(pathlib.Path.cwd())} с плейсхолдерами {{VERSION}}, {{PREV_VERSION}}"
        )


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 3: git log since last tag")
    parser.add_argument("--tag", type=str, help="собрать изменения с указанного тега (по умолчанию — последний тег)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    print("[stage3] Поиск коммитов после последнего тега...")
    
    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage3] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[stage3] Проверяем каталог: {packages_dir}")
    
    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        print(f"[stage3] Проверяем пакет: {pkg.name}")
        process_package(
            pkg,
            cfg,
            dry_run=args.dry_run or cfg.get("dry_run", False),
            include_diff=True,
            from_tag=args.tag,
        )
        # Проверяем был ли создан файл
        changes_file = (pathlib.Path.cwd() / cfg.get("changes_output_dir", "release_tool/changes") / pkg.name / cfg["changes_since_tag_filename"])
        if changes_file.exists():
            processed += 1
    
    if processed == 0:
        print("[stage3] ✅ Нет пакетов с новыми коммитами после последнего тега")
    else:
        print(f"[stage3] ✅ Завершено. Обработано пакетов: {processed}")
        print(f"[stage3] Файлы изменений сохранены в: {cfg.get('changes_output_dir', 'release_tool/changes')}")


if __name__ == "__main__":
    run() 