from __future__ import annotations

"""Утилиты для анализа состояния git-репозитория (ahead/behind, незакоммиченные изменения).

Модуль используется в нескольких стадиях release_tool, чтобы не дублировать
логику подсчёта статуса ветки.
"""

import pathlib
from dataclasses import dataclass

from .git_helpers import remote_branch_exists, calc_ahead_behind
from .git_utils import has_uncommitted_changes


@dataclass(slots=True)
class RepoStatus:
    """Сводная информация о состоянии рабочей ветки по отношению к remote."""

    ahead: int  # количество локальных коммитов, отсутствующих на remote
    behind: int  # количество remote-коммитов, отсутствующих локально
    uncommitted: bool  # есть ли незакоммиченные изменения/файлы


def analyze_repo_status(repo: pathlib.Path, branch: str, remote: str = "origin") -> RepoStatus:  # noqa: D401
    """Возвращает `RepoStatus` для *repo*.

    1. Если ветка *remote/branch* существует — считаем `ahead`/`behind`.
    2. Иначе `ahead == behind == 0` (ветка ещё не опубликована).
    3. `uncommitted` вычисляется через `git status --porcelain`.
    """

    if remote_branch_exists(repo, remote, branch):
        ahead, behind = calc_ahead_behind(repo, branch, f"{remote}/{branch}")
    else:
        ahead = behind = 0

    uncommitted = has_uncommitted_changes(repo)

    return RepoStatus(ahead=ahead, behind=behind, uncommitted=uncommitted) 