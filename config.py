import pathlib
import sys

try:
    import tomllib  # type: ignore  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def find_config_file() -> pathlib.Path:
    """Находит конфигурационный файл в порядке приоритета:
    1. release_tool.toml в корне проекта (текущая рабочая директория)
    2. release_tool/release_tool.toml (в submodule)
    3. Встроенная конфигурация в модуле
    """
    # Порядок поиска конфигурации
    search_paths = [
        pathlib.Path.cwd() / "release_tool.toml",  # Корень проекта
        pathlib.Path.cwd() / "release_tool" / "release_tool.toml",  # В submodule
        pathlib.Path(__file__).resolve().parent / "release_tool.toml",  # В модуле
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    # Если ничего не найдено, возвращаем путь к дефолтной конфигурации для ошибки
    return search_paths[0]


def load_config(config_path: pathlib.Path | str | None = None) -> dict:
    """Загружает конфигурацию инструмента релиза.

    Parameters
    ----------
    config_path : pathlib.Path | str | None
        Путь к конфигурационному файлу. Если None, автоматически ищет конфигурацию.

    Returns
    -------
    dict
        Секция `[tool.release_tool]` из TOML-файла.
    """
    if config_path:
        path = pathlib.Path(config_path)
    else:
        path = find_config_file()
    
    if not path.exists():
        print(f"[release_tool] Конфигурационный файл не найден.", file=sys.stderr)
        print(f"[release_tool] Искал в:", file=sys.stderr)
        print(f"[release_tool]   1. {pathlib.Path.cwd() / 'release_tool.toml'} (корень проекта)", file=sys.stderr)
        print(f"[release_tool]   2. {pathlib.Path.cwd() / 'release_tool' / 'release_tool.toml'} (submodule)", file=sys.stderr)
        print(f"[release_tool]   3. {pathlib.Path(__file__).resolve().parent / 'release_tool.toml'} (в модуле)", file=sys.stderr)
        sys.exit(1)

    with path.open("rb") as fh:
        toml_data: dict = tomllib.load(fh)

    try:
        cfg = toml_data["tool"]["release_tool"]
        # defaults for new keys
        cfg.setdefault("changes_uncommitted_filename", "changes_uncommitted.txt")
        cfg.setdefault("changes_since_tag_filename", "changes_since_tag.txt")
        cfg.setdefault("tag_message_filename", "tag_message.txt")
        cfg.setdefault("changes_output_dir", "release_tool/changes")
        
        # Добавляем информацию о том, откуда загружена конфигурация
        cfg["_config_source"] = str(path.relative_to(pathlib.Path.cwd()))
        
        return cfg
    except KeyError as exc:
        print("[release_tool] В конфигурации отсутствует секция [tool.release_tool]", file=sys.stderr)
        raise SystemExit(1) from exc 