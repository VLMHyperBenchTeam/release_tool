"""
Stage 2: делает коммит и/или push во всех пакетах, используя подготовленные сообщения.

Запуск:
    python -m release_tool.stage2 [--commit] [--push] [--dry-run]

--commit  создать коммиты по файлам commit_message.txt
--push    выполнить git push
Если ни один флаг не указан, по умолчанию выполняется только --commit.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from .config import load_config
from .git_utils import commit_all, _push_repo, has_commits_to_push


def process_package(pkg_path: pathlib.Path, cfg: dict, push: bool, dry_run: bool = False) -> None:
    root = pathlib.Path.cwd()
    changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg_path.name
    msg_file = changes_dir / cfg["commit_message_filename"]
    if not msg_file.exists():
        print(f"[stage2]   {pkg_path.name}: файл commit-сообщения не найден")
        return

    message = msg_file.read_text(encoding="utf-8").strip()
    if not message:
        print(f"[stage2]   {pkg_path.name}: пустое commit-сообщение")
        return

    commit_all(pkg_path, message, remote=cfg.get("git_remote", "origin"), push=push, dry_run=dry_run)
    print(f"[stage2]   ✅ {pkg_path.name}: commit создан{' и отправлен' if push else ''}")


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Stage 2: commit и/или push изменений по пакетам")
    parser.add_argument("--commit", action="store_true", help="создать коммит по подготовленным сообщениям")
    parser.add_argument("--push", action="store_true", help="выполнить git push для пакетов")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.commit and not args.push:
        # Для обратной совместимости по умолчанию совершаем commit (без push)
        args.commit = True

    actions_descr = []
    if args.commit:
        actions_descr.append("коммит")
    if args.push:
        actions_descr.append("push")
    action = " и ".join(actions_descr)
    print(f"[stage2] Выполняем {action} для пакетов с подготовленными сообщениями...")
    
    root = pathlib.Path.cwd()
    packages_dir = root / cfg["packages_dir"]
    if not packages_dir.is_dir():
        print(f"[stage2] каталог пакетов не найден: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        print(f"[stage2] Проверяем пакет: {pkg.name}")
        # Commit (если запрошен)
        if args.commit:
            process_package(pkg, cfg, push=False, dry_run=args.dry_run or cfg.get("dry_run", False))

        # Push (если запрошен)
        if args.push:
            remote_name = cfg.get("git_remote", "origin")
            try:
                if has_commits_to_push(pkg, remote=remote_name):
                    _push_repo(pkg, remote_name)
                    print(f"[stage2]   ✅ {pkg.name}: изменения отправлены")
                else:
                    print(f"[stage2]   📭 {pkg.name}: изменений нет")
            except Exception as exc:  # noqa: BLE001
                print(f"[stage2]   ❌ {pkg.name}: push завершился ошибкой: {exc}")

        # Проверяем, был ли пакет обработан
        changes_dir = root / cfg.get("changes_output_dir", "release_tool/changes") / pkg.name
        msg_file = changes_dir / cfg["commit_message_filename"]
        if args.commit and msg_file.exists() and msg_file.read_text(encoding="utf-8").strip():
            processed += 1
    
    if processed == 0:
        print("[stage2] ✅ Нет пакетов с подготовленными commit-сообщениями")
    else:
        print(f"[stage2] ✅ Завершено. Обработано пакетов: {processed}")


if __name__ == "__main__":
    run() 