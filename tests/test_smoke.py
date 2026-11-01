"""P0 smoke tests: the smallest checks that the project runs and is set up correctly."""

import re
import sys
from pathlib import Path

import markcap

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache"}


def test_python_is_311_or_newer():
    assert sys.version_info >= (3, 11)


def test_package_has_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+", markcap.__version__)


def test_contract_files_exist():
    for name in ("PAPER_SPEC.md", "REPRODUCTION_NOTES.md", "VERIFICATION.md", "CLAUDE.md", "LICENSE"):
        assert (ROOT / name).is_file(), name


def test_old_project_name_is_not_used():
    old = "Driver" + "Lens"  # split so this file does not match itself
    suffixes = {".md", ".py", ".toml", ".in", ".yaml", ".yml", ".txt", ".example"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or SKIP & set(path.parts) or path.suffix not in suffixes:
            continue
        assert old.lower() not in path.read_text(encoding="utf-8").lower(), path
