import os
from pathlib import Path

MODEL_RESEARCH = "claude-opus-4-6"
MODEL_WRITER = "claude-sonnet-4-6"
MODEL_EDITOR = "claude-sonnet-4-6"
MODEL_FACTS = "claude-haiku-4-5-20251001"

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent / "workspace"


def workspace_path(slug: str) -> Path:
    return WORKSPACE_ROOT / slug


def ensure_workspace(slug: str) -> Path:
    path = workspace_path(slug)
    path.mkdir(parents=True, exist_ok=True)
    (path / "draft").mkdir(exist_ok=True)
    (path / "reviews").mkdir(exist_ok=True)
    return path


def file_exists_prompt(filepath: Path, label: str) -> bool:
    """If filepath exists, ask the user whether to overwrite. Returns True if we should proceed."""
    if not filepath.exists():
        return True
    answer = input(f"{label} already exists at {filepath}. Overwrite? (y/n): ").strip().lower()
    return answer == "y"


def pause_for_review(message: str):
    input(f"{message} Press Enter to continue or Ctrl+C to stop.")
