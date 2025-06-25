from __future__ import annotations

"""Вспомогательные git-утилиты для скриптов release_tool (Stage 0/…)."""

import contextlib
import pathlib
from typing import Iterator, Optional

from .git_utils import _run_git, GitError


# ---------------------------------------------------------------------------
# Вспомогательные типы


class _StashResult:  # noqa: D101 – simple container for stash info
    """Результат работы контекст-менеджера `temporary_stash`."""

    __slots__ = ("kept",)

    def __init__(self, kept: bool = False) -> None:  # noqa: D401
        self.kept: bool = kept


def remote_branch_exists(repo: pathlib.Path, remote: str, branch: str) -> bool:
    """Проверяет наличие ветки *remote/branch* на удалённом репозитории."""
    return _run_git(repo, ["rev-parse", "--verify", f"{remote}/{branch}"], capture=True).returncode == 0


def local_branch_exists(repo: pathlib.Path, branch: str) -> bool:
    """Проверяет существование локальной ветки."""
    return _run_git(repo, ["show-ref", "--verify", f"refs/heads/{branch}"], capture=True).returncode == 0


def fast_forward(repo: pathlib.Path, target_ref: str) -> bool:
    """Пытается fast-forward текущей ветки до *target_ref*.

    Возвращает True, если fast-forward выполнен, False — если нечего перемещать.
    Бросает GitError, если fast-forward невозможен (divergent history).
    """
    proc = _run_git(repo, ["merge", "--ff-only", target_ref], capture=True)
    if proc.returncode == 0:
        return proc.stdout.strip() != ""  # было ли перемещение HEAD
    if "already up to date" in (proc.stderr or proc.stdout or ""):
        return False
    raise GitError(proc.stderr or proc.stdout)


@contextlib.contextmanager
def temporary_stash(
    repo: pathlib.Path,
    *,
    enabled: bool = True,
    include_untracked: bool = True,
    message: str = "stage0-auto-stash",
    keep: bool = False,
) -> Iterator["_StashResult"]:
    """Временно убирает изменения `git stash`-ем, а после выхода восстанавливает.

    Возвращает через *with* объект с полем ``kept``:
    True  – stash сохранён (есть конфликты или запрошено *keep*),
    False – stash удалён / не создавался.
    """

    result = _StashResult(False)

    if not enabled:
        # stash не требуется – просто выполняем тело *with*
        yield result
        return

    # ---- stash push ----------------------------------------------------
    push_args = [
        "stash",
        "push",
        "--include-untracked" if include_untracked else "--keep-index",
        "-m",
        message,
    ]
    _run_git(repo, push_args, capture=False)

    try:
        yield result  # возвращаем объект, который будет заполнен при выходе
    finally:
        # ---- stash pop --------------------------------------------------
        _run_git(repo, ["stash", "pop"], capture=False)

        # Проверяем конфликты после pop
        conflicts = _run_git(repo, ["diff", "--name-only", "--diff-filter=U"], capture=True).stdout.strip()
        has_conflicts = bool(conflicts)

        if has_conflicts or keep:
            # stash сохраняем для анализа или по запросу пользователя
            result.kept = True
        else:
            # Удаляем только что восстановленный stash, если он наш
            list_proc = _run_git(repo, ["stash", "list"], capture=True)
            first_line: Optional[str] = list_proc.stdout.split("\n")[0] if list_proc.stdout else None
            if first_line and message in first_line:
                ref = first_line.split(":", 1)[0]
                _run_git(repo, ["stash", "drop", ref], capture=False)
            result.kept = False


# ---------------------------------------------------------------------------
# high-level helpers


def checkout_branch(repo: pathlib.Path, branch: str, start_point: str | None = None) -> None:
    """Создаёт/переключается на *branch*.

    Если *start_point* передан → `git checkout -B branch <start_point>`.
    Иначе `git checkout branch`.
    """
    args = ["checkout", branch] if start_point is None else ["checkout", "-B", branch, start_point]
    _run_git(repo, args, capture=False)


def ensure_tracking(repo: pathlib.Path, branch: str, remote: str) -> None:
    """Настраивает upstream *branch* → *remote/branch*, если remote-ветка существует."""
    if remote_branch_exists(repo, remote, branch):
        _run_git(repo, ["branch", "--set-upstream-to", f"{remote}/{branch}", branch], capture=False)


def calc_ahead_behind(repo: pathlib.Path, branch: str, remote_ref: str) -> tuple[int, int]:
    """Возвращает (ahead, behind) между *branch* и *remote_ref*.

    Если *remote_ref* не существует — (0, 0).
    """
    proc = _run_git(repo, [
        "rev-list",
        "--left-right",
        "--count",
        f"{branch}...{remote_ref}",
    ], capture=True)

    output = proc.stdout.strip()
    if proc.returncode != 0 or not output:
        return 0, 0

    parts = output.split()
    if len(parts) == 2:
        left, right = parts
    elif len(parts) == 1:
        # git может вернуть только один счётчик, если одна из веток отсутствует
        left, right = parts[0], "0"
    else:
        return 0, 0

    return int(left), int(right) 