from pathlib import Path


PARENT_DIR_NAMES = ["Fenrir", "fenrir", "s", "FTS", "fts"]


def get_project_root(target_override: str | None = None) -> Path:
    """
    Returns the Path to the Fenrir project root directory.
    """
    current_path = Path(__file__).resolve()
    if target_override:
        for parent in current_path.parents:
            if parent.name == target_override:
                return parent

    for parent in current_path.parents:
        if parent.name in PARENT_DIR_NAMES:
            return parent
    raise RuntimeError(f"Fenrir project root directory not found. \n {current_path}")
