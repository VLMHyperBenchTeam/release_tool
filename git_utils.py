"""Утилиты для работы с `git` через subprocess."""
from __future__ import annotations

import subprocess
import pathlib
from typing import List, Optional


class GitError(RuntimeError):
    """Исключение git-операций."""


def _run_git(path: pathlib.Path, args: List[str], capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Выполнить git-команду в каталоге *path*.

    Parameters
    ----------
    path : pathlib.Path
        Корень репозитория.
    args : List[str]
        Аргументы команды после `git`.
    capture : bool, default True
        Захватывать stdout/err.
    """
    kwargs = {
        "text": True,
        "encoding": "utf-8",
        "check": False,
        "cwd": str(path),
    }
    if capture:
        kwargs |= {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    result = subprocess.run(["git", *args], **kwargs)  # type: ignore[arg-type]
    return result


def has_changes_since_last_tag(repo_path: pathlib.Path) -> bool:
    """Проверяет есть ли коммиты после последнего тега."""
    last_tag = get_last_tag(repo_path)
    if last_tag is None:
        # Нет тегов — значит изменения точно есть
        return True
    proc = _run_git(repo_path, ["rev-list", f"{last_tag}..HEAD", "--count"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return int(proc.stdout.strip() or "0") > 0


def get_last_tag(repo_path: pathlib.Path) -> Optional[str]:
    """Возвращает последний тег, либо *None* если тега нет."""
    proc = _run_git(repo_path, ["describe", "--tags", "--abbrev=0"])
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def get_log_since_tag(repo_path: pathlib.Path, tag: Optional[str]) -> str:
    """Возвращает git log (subject + body) начиная с *tag* (или со всего репо, если *tag* == None)."""
    revspec = f"{tag}..HEAD" if tag else "HEAD"
    fmt = "%h %s"
    proc = _run_git(repo_path, ["log", revspec, f"--pretty=format:{fmt}"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def commit_and_tag(
    repo_path: pathlib.Path,
    commit_message: str,
    tag_name: str,
    remote: str = "origin",
    dry_run: bool = False,
) -> None:
    """Коммитит все индексированные изменения, создаёт тег и пушит (если *dry_run* == False)."""
    if dry_run:
        print(f"[dry-run] git -C {repo_path} commit -m \"{commit_message}\"")
        print(f"[dry-run] git -C {repo_path} tag -a {tag_name} -m \"{commit_message}\"")
        print(f"[dry-run] git -C {repo_path} push {remote}")
        print(f"[dry-run] git -C {repo_path} push {remote} {tag_name}")
        return

    for cmd in [
        ["commit", "-m", commit_message],
        ["tag", "-a", tag_name, "-m", commit_message],
        ["push", remote],
        ["push", remote, tag_name],
    ]:
        proc = _run_git(repo_path, cmd, capture=False)
        if proc.returncode != 0:
            raise GitError(f"git {' '.join(cmd)} failed in {repo_path}")


def get_uncommitted_changes(repo_path: pathlib.Path) -> str:
    """Возвращает `git status --porcelain` (модифицированные/новые файлы)."""
    proc = _run_git(repo_path, ["status", "--porcelain"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def has_uncommitted_changes(repo_path: pathlib.Path) -> bool:
    """True если есть изменения в рабочем каталоге (включая untracked)."""
    return bool(get_uncommitted_changes(repo_path))


def commit_all(repo_path: pathlib.Path, commit_message: str, remote: str = "origin", push: bool = False, dry_run: bool = False) -> None:
    """Коммитит все индексированные изменения (git add -A) и при необходимости пушит."""

    if dry_run:
        print(f"[dry-run] git -C {repo_path} add -A")
        print(f"[dry-run] git -C {repo_path} commit -m \"{commit_message}\"")
        if push:
            print(f"[dry-run] git -C {repo_path} push {remote}")
        return

    proc = _run_git(repo_path, ["add", "-A"], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)

    proc = _run_git(repo_path, ["commit", "-m", commit_message], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)

    if push:
        proc = _run_git(repo_path, ["push", remote], capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr)


def get_diff_stat(repo_path: pathlib.Path) -> str:
    """Возвращает `git diff --stat` для рабочего каталога."""
    proc = _run_git(repo_path, ["diff", "--stat"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def get_full_diff(repo_path: pathlib.Path) -> str:
    """Возвращает `git diff` (полный текст изменений) для рабочего каталога."""
    proc = _run_git(repo_path, ["diff"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip() 