from pathlib import Path


def get_project_root() -> Path:
    """
    Returns the Path to the Fenrir project root directory.
    """
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        # Fenrir becomes /s/ in CI
        if parent.name == "Fenrir" or parent.name == "fenrir" or parent.name == "s":
            return parent
    raise RuntimeError("Fenrir project root directory not found.")
