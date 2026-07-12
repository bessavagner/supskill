"""SK-007: package imports, CLI shim exists and is executable, zero runtime deps."""

import os
import tomllib
from pathlib import Path

import pytest

import supskill_state
from supskill_state.cli import build_parser
from supskill_state.errors import StateError

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_importable_and_versioned():
    assert supskill_state.__version__


def test_state_error_is_an_exception():
    assert issubclass(StateError, Exception)


def test_cli_requires_a_subcommand():
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args([])
    assert excinfo.value.code == 2


def test_shim_exists_and_is_executable():
    shim = REPO_ROOT / "scripts" / "supskill-state"
    assert shim.exists()
    assert os.access(shim, os.X_OK)


def test_zero_runtime_dependencies():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == []
