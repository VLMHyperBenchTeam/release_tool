import pathlib
import sys

try:
    import tomllib  # type: ignore  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


DEFAULT_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "release_tool.toml"


def load_config(config_path: pathlib.Path | str | None = None) -> dict:
    """Загружает конфигурацию инструмента релиза.

    Parameters
    ----------
    config_path : pathlib.Path | str | None
        Путь к конфигурационному файлу. Если *None*, берётся `DEFAULT_CONFIG_PATH`.

    Returns
    -------
    dict
        Секция `[tool.release_tool]` из TOML-файла.
    """
    path = pathlib.Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        print(f"[release_tool] Конфигурационный файл не найден: {path}", file=sys.stderr)
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
        return cfg
    except KeyError as exc:
        print("[release_tool] В конфигурации отсутствует секция [tool.release_tool]", file=sys.stderr)
        raise SystemExit(1) from exc 