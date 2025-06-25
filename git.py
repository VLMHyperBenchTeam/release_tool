# deprecated shim — переехал в release_tool.core.git
from release_tool.core.git import *  # type: ignore  # noqa: F401,F403

if __name__ == "__main__":
    from release_tool.core.git import GitRepo  # type: ignore
    import pathlib, sys

    repo_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
    print(GitRepo(repo_path).current_branch()) 