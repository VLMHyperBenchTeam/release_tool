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
from dataclasses import dataclass

from .config import load_config
from .git_utils import _push_repo, _run_git, has_commits_to_push, GitError
from .git_helpers import (
    remote_branch_exists,
    local_branch_exists,
    fast_forward,
    checkout_branch,
    ensure_tracking,
    calc_ahead_behind,
    temporary_stash,
)


@dataclass
class PackageResult:
    name: str
    push_done: bool
    stash_kept: bool
    ahead: int
    behind: int
    uncommitted: bool


def _process_package(
    pkg: pathlib.Path,
    branch: str,
    base: str,
    remote: str,
    push: bool,
    dry_run: bool,
    no_stash: bool,
    stash_name: str,
    keep_stash: bool,
    fallback_head: bool,
    fallback_local: bool,
) -> tuple[bool, bool, int, int]:
    """Готовит dev-ветку *branch* в пакете *pkg*.

    Возвращает:
        push_done, stash_kept, ahead, behind
    """

    # --- dry-run ---------------------------------------------------------
    if dry_run:
        print(f"[stage0]   [dry-run] git -C {pkg} fetch {remote}")
        print(f"[stage0]   [dry-run] git -C {pkg} checkout -B {branch} {remote}/{base}")
        if push:
            print(f"[stage0]   [dry-run] git -C {pkg} push --set-upstream {remote} {branch}")
        return False, False, 0, 0

    # --------------------------------------------------------------------
    _run_git(pkg, ["fetch", remote], capture=False)

    remote_dev_exists = remote_branch_exists(pkg, remote, branch)
    local_dev_exists = local_branch_exists(pkg, branch)

    stash_kept = False

    if remote_dev_exists:
        # --- существующая ветка на remote --------------------------------
        start_point = None if local_dev_exists else f"{remote}/{branch}"
        checkout_branch(pkg, branch, start_point)

        try:
            fast_forward(pkg, f"{remote}/{branch}")
        except GitError:
            print(f"[stage0]   ⚠️  {pkg.name}: локальная {branch} расходится с {remote}/{branch} — manual rebase/push")

    else:
        # --- создаём dev из base ----------------------------------------
        # Определяем ref, от которого будем создавать ветку.
        if remote_branch_exists(pkg, remote, base):
            start_ref = f"{remote}/{base}"
        elif fallback_head:
            head_proc = _run_git(pkg, ["symbolic-ref", f"refs/remotes/{remote}/HEAD"], capture=True)
            if head_proc.returncode == 0:
                default = head_proc.stdout.strip().split("/")[-1] or base
                print(f"[stage0]   ℹ️  {pkg.name}: используем дефолтную ветку {default} вместо {base}")
                start_ref = f"{remote}/{default}"
            elif fallback_local:
                start_ref = base  # локальный base
            else:
                start_ref = base
        else:
            start_ref = base

        # Проверяем, нужны ли stash-операции.
        workspace_dirty = bool(_run_git(pkg, ["status", "--porcelain"], capture=True).stdout.strip())
        if workspace_dirty and no_stash:
            print(f"[stage0]   ❌ {pkg.name}: есть незакоммиченные изменения, --no-stash установлен — пакет пропущен")
            return False, False, 0, 0

        with temporary_stash(
            pkg,
            enabled=workspace_dirty and not no_stash,
            message=stash_name,
            keep=keep_stash,
        ) as ts:
            checkout_branch(pkg, branch, start_ref)
        stash_kept = ts.kept

    # --- настройка upstream --------------------------------------------
    ensure_tracking(pkg, branch, remote)

    # --- push -----------------------------------------------------------
    push_done = False
    if push and has_commits_to_push(pkg, remote):
        _push_repo(pkg, remote)
        print(f"[stage0]   🚀 ветка {branch} отправлена")
        push_done = True
    elif push:
        print("[stage0]   📭 изменений нет — push пропущен")

    # --- ahead/behind ---------------------------------------------------
    if remote_branch_exists(pkg, remote, branch):
        ahead, behind = calc_ahead_behind(pkg, branch, f"{remote}/{branch}")
    else:
        ahead = behind = 0

    print(f"[stage0]   ✅ {pkg.name}: подготовлена ветка {branch} (от {base})")

    return push_done, stash_kept, ahead, behind


def run(argv: list[str] | None = None) -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Stage 0: prepare dev branches from base branch")
    parser.add_argument("--branch", default="dev_branch", help="Имя dev-ветки")
    parser.add_argument("--base-branch", default="main", help="Базовая ветка, от которой создаётся dev-ветка")
    parser.add_argument("--push", action="store_true", help="Отправить ветку после создания")
    parser.add_argument("--dry-run", action="store_true")
    # дополнительные флаги
    parser.add_argument("--no-stash", action="store_true", help="Не выполнять auto-stash, если есть изменения (завершить ошибкой)")
    parser.add_argument("--stash-name", help="Пользовательский заголовок stash, по умолчанию stage0-auto-<branch>")
    parser.add_argument("--keep-stash", action="store_true", help="Не удалять созданный stash после успешного pop без конфликтов")
    parser.add_argument("--fallback-head", dest="fallback_head", action=argparse.BooleanOptionalAction, default=True, help="Использовать origin/HEAD если <base_branch> не найден")
    parser.add_argument("--fallback-local", dest="fallback_local", action=argparse.BooleanOptionalAction, default=True, help="Использовать локальную ветку <base_branch> если remote отсутствует")
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
    results: list[PackageResult] = []
    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
        if not (changes_root / pkg.name).exists():
            # пакет не участвует в текущем релизе
            continue
        # Проверяем, что remote существует
        remote_chk = _run_git(pkg, ["remote", "get-url", remote_name])
        if remote_chk.returncode != 0:
            print(f"[stage0]   ❌ {pkg.name}: remote '{remote_name}' не найден — пропуск")
            continue

        print(f"[stage0] Обрабатываем пакет: {pkg.name}")
        push_done, stash_kept, ahead, behind = _process_package(
            pkg,
            args.branch,
            args.base_branch,
            remote_name,
            args.push,
            dry_run=args.dry_run or cfg.get("dry_run", False),
            no_stash=args.no_stash,
            stash_name=args.stash_name or f"stage0-auto-{args.branch}",
            keep_stash=args.keep_stash,
            fallback_head=args.fallback_head,
            fallback_local=args.fallback_local,
        )
        # gather summary
        uncommitted_proc = _run_git(pkg, ["status", "--porcelain"])
        uncommitted_flag = bool(uncommitted_proc.stdout.strip())

        results.append(
            PackageResult(
                name=pkg.name,
                push_done=push_done,
                stash_kept=stash_kept,
                ahead=ahead,
                behind=behind,
                uncommitted=uncommitted_flag,
            )
        )
        processed += 1

    # Формируем красивый отчёт
    lines: list[str] = []
    for r in results:
        parts: list[str] = []
        if r.ahead:
            parts.append(f"ahead:{r.ahead}")
        if r.behind:
            parts.append(f"behind:{r.behind}")
        if r.stash_kept:
            parts.append("stash")
        if r.uncommitted:
            parts.append("uncommitted")
        status = ", ".join(parts) if parts else "ok"
        push_status = "отправлена" if r.push_done else "локально"
        lines.append(f"  • {r.name:<15} — {push_status}; {status}")

    print(f"[stage0] ✅ Завершено. Обработано пакетов: {processed}\n[stage0] Итог:\n" + "\n".join(lines))


if __name__ == "__main__":
    run() 