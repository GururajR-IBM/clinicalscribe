"""Prompt registry. Each agent loads its prompt by (name, version)."""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

__all__ = ["TEMPLATES_DIR"]
