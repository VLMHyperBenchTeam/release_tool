"""Stage 3: собирает список коммитов после последнего тега.

Создаёт `<changes_since_tag_filename>` внутри пакета.

Запуск:
    python -m release_tool.stage3 [--dry-run] [--diff]
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
)


def _build_changes_text(
    commits_log: str,
    diff_text: str | None,
) -> str:
    """Формирует итоговый текст файла изменений.

    Если *diff_text* не *None*, то добавляется секция с diff.
    """

    if commits_log and diff_text:
        return f"{commits_log}\n\n==== diff ====\n{diff_text}\n"

    if commits_log:
        return commits_log + "\n"

    # Только diff
    return f"==== diff ====\n{diff_text}\n"


def process_package(
    pkg_path: pathlib.Path,
    cfg: dict,
    dry_run: bool = False,
    include_diff: bool = False,
) -> None:
    if not has_changes_since_last_tag(pkg_path):
        print(f"[stage3]   {pkg_path.name}: нет новых коммитов после последнего тега")
        return

    last_tag = get_last_tag(pkg_path)
    log = get_log_since_tag(pkg_path, last_tag)

    diff_txt: str | None = None
    if include_diff:
        diff_txt = get_diff_since_tag(pkg_path, last_tag)

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
        if not dry_run:
            tag_msg_file.write_text("", encoding="utf-8")
        print(f"[stage3]   📝 {pkg_path.name}: создан пустой файл {tag_msg_file.relative_to(pathlib.Path.cwd())}")


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 3: git log since last tag")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--diff",
        action="store_true",
        help="добавить git diff между последним тегом и HEAD в файл изменений",
    )
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
            include_diff=args.diff,
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