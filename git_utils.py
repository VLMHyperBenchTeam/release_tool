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
    """Возвращает список коммитов (полные сообщения) после *tag* в читабельном виде.

    Формат вывода:
        коммит 1
        <subject>
        <body>

        коммит 2
        <subject>
        <body>
        ...
    """
    revspec = f"{tag}..HEAD" if tag else "HEAD"

    # Используем NUL-разделитель, чтобы безопасно разбить список коммитов
    fmt = "%s%n%b%x00"  # subject, затем body, затем NUL-символ
    proc = _run_git(repo_path, ["log", revspec, f"--pretty=format:{fmt}"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)

    raw_output = proc.stdout
    if not raw_output:
        return ""

    commits_raw = raw_output.split("\x00")
    commits = [c.strip() for c in commits_raw if c.strip()]

    formatted: list[str] = []
    for idx, commit_msg in enumerate(commits, 1):
        # Если коммит состоит только из subject строки, body может отсутствовать
        formatted.append(f"коммит {idx}\n{commit_msg.strip()}\n")

    # Между коммитами будет пустая строка благодаря завершающему \n в formatted.append
    return "\n".join(formatted).strip()


def commit_and_tag(
    repo_path: pathlib.Path,
    commit_message: str,
    tag_name: str,
    remote: str = "origin",
    push: bool = False,
    dry_run: bool = False,
) -> None:
    """Коммитит все индексированные изменения, создаёт тег.

    Если *push* == True, выполняет push коммита и тега.
    Если *dry_run* == True, команды лишь выводятся на экран.
    """
    if dry_run:
        print(f"[dry-run] git -C {repo_path} commit -m \"{commit_message}\"")
        print(f"[dry-run] git -C {repo_path} tag -a {tag_name} -m \"{commit_message}\"")
        if push:
            print(f"[dry-run] git -C {repo_path} push {remote}")
            print(f"[dry-run] git -C {repo_path} push {remote} {tag_name}")
        return

    # Always commit and create tag locally
    for cmd in [
        ["commit", "-m", commit_message],
        ["tag", "-a", tag_name, "-m", commit_message],
    ]:
        proc = _run_git(repo_path, cmd, capture=False)
        if proc.returncode != 0:
            raise GitError(proc.stderr or f"git {' '.join(cmd)} failed in {repo_path}")

    # Push only if requested
    if push:
        for cmd in [
            ["push", remote],
            ["push", remote, tag_name],
        ]:
            proc = _run_git(repo_path, cmd, capture=False)
            if proc.returncode != 0:
                raise GitError(proc.stderr or f"git {' '.join(cmd)} failed in {repo_path}")


def get_uncommitted_changes(repo_path: pathlib.Path) -> str:
    """Возвращает `git status --porcelain` (модифицированные/новые файлы)."""
    proc = _run_git(repo_path, ["status", "--porcelain"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def has_uncommitted_changes(repo_path: pathlib.Path) -> bool:
    """True если есть изменения в рабочем каталоге (включая untracked)."""
    return bool(get_uncommitted_changes(repo_path))


def _get_current_branch(repo_path: pathlib.Path) -> str:
    """Возвращает имя текущей ветки."""
    proc = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def commit_all(repo_path: pathlib.Path, commit_message: str, remote: str = "origin", push: bool = False, dry_run: bool = False) -> None:
    """Коммитит все индексированные изменения (git add -A) и при необходимости пушит.

    Если push завершается ошибкой "set upstream first", выполняется повторная
    попытка с флагом `--set-upstream` для текущей ветки.
    """

    if dry_run:
        print(f"[dry-run] git -C {repo_path} add -A")
        print(f"[dry-run] git -C {repo_path} commit -m \"{commit_message}\"")
        if push:
            print(f"[dry-run] git -C {repo_path} push {remote}")
        return

    proc = _run_git(repo_path, ["add", "-A"], capture=False)
    if proc.returncode != 0:
        raise GitError(proc.stderr)

    proc = _run_git(repo_path, ["commit", "-m", commit_message], capture=True)
    if proc.returncode != 0:
        # Git возвращает код 1, если нечего коммитить.
        combined_output = (proc.stdout or "") + (proc.stderr or "")
        if "nothing to commit" in combined_output or "nothing added to commit" in combined_output:
            # Ничего коммитить — игнорируем ошибку и продолжаем к push.
            print(f"[git_utils] {repo_path.name}: нет изменений для коммита (пропускаем commit)")
        else:
            raise GitError(proc.stderr or proc.stdout)

    if push:
        _push_repo(repo_path, remote)


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


def get_diff_since_tag(repo_path: pathlib.Path, tag: Optional[str]) -> str:
    """Возвращает `git diff` между *tag* и HEAD.

    Если *tag* равен *None*, то возвращается diff для последнего коммита (HEAD^..HEAD).
    """
    revspec = f"{tag}..HEAD" if tag else "HEAD^..HEAD"  # если тега нет, берём diff одного последнего коммита
    proc = _run_git(repo_path, ["diff", revspec])
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return proc.stdout.strip()


def _push_repo(repo_path: pathlib.Path, remote: str = "origin") -> None:
    """Выполняет `git push` с резервным запуском `--set-upstream`, если у ветки нет upstream."""
    proc = _run_git(repo_path, ["push", remote], capture=True)
    if proc.returncode == 0:
        return

    stderr = proc.stderr or ""
    # Если нет upstream для текущей ветки, повторяем push с --set-upstream
    if "set upstream" in stderr or "--set-upstream" in stderr or "have no upstream" in stderr:
        branch = _get_current_branch(repo_path)
        fallback_cmd = ["push", "--set-upstream", remote, branch]
        print(f"[git_utils] upstream not set, выполняем: git {' '.join(fallback_cmd)}")
        fallback_proc = _run_git(repo_path, fallback_cmd, capture=True)
        if fallback_proc.returncode != 0:
            raise GitError(fallback_proc.stderr or stderr)
    else:
        raise GitError(stderr)


def has_commits_to_push(repo_path: pathlib.Path, remote: str = "origin") -> bool:
    """Возвращает *True*, если локальная ветка содержит коммиты, отсутствующие в *remote*.

    Алгоритм:
    1. Определяем имя текущей ветки.
    2. Проверяем, существует ли соответствующая ветка в *remote*.
       Если нет — считаем, что пушить есть что (ветка новая).
    3. Считаем количество коммитов `rev-list <remote>/<branch>..HEAD`.
    """
    branch = _get_current_branch(repo_path)

    # Проверяем, есть ли ветка на remote
    proc_check = _run_git(repo_path, ["rev-parse", "--verify", f"{remote}/{branch}"], capture=True)
    remote_branch_exists = proc_check.returncode == 0

    if not remote_branch_exists:
        # Ветка ещё не опубликована — есть что пушить
        return True

    proc = _run_git(repo_path, ["rev-list", "--count", f"{remote}/{branch}..HEAD"], capture=True)
    if proc.returncode != 0:
        raise GitError(proc.stderr)
    return int(proc.stdout.strip() or "0") > 0 