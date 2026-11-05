"""Discover local GitHub Actions workflow files without reading them."""

import stat
from pathlib import Path


def discover_workflows(repository_path: Path) -> list[Path]:
    """Return sorted workflow paths, rejecting linked workflow directories."""
    repository_path = Path(repository_path)
    if not stat.S_ISDIR(repository_path.stat().st_mode):
        raise NotADirectoryError(
            f"Repository path is not a directory: {repository_path}"
        )

    directory = repository_path
    for component in (".github", "workflows"):
        directory = directory / component
        try:
            mode = directory.lstat().st_mode
        except FileNotFoundError:
            return []
        if stat.S_ISLNK(mode):
            raise ValueError(
                f"Workflow directory must not be a symbolic link: {directory}"
            )
        if not stat.S_ISDIR(mode):
            raise NotADirectoryError(f"Workflow path is not a directory: {directory}")

    return sorted(
        path
        for path in directory.iterdir()
        if path.suffix in {".yml", ".yaml"} and stat.S_ISREG(path.lstat().st_mode)
    )
