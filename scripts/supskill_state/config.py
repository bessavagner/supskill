"""Per-project config at .supskill/config.json - the story-id prefix (SK-064).

Separate from state.json: the story-id scheme is a property of the project,
not of one sprint run, so it must survive `init --archive` instead of
resetting with each sprint. proofs.py and plan_coverage.py stay the sole
owners of the grammars built from this prefix - this module only stores and
validates the string.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import store
from .errors import StateError

DEFAULT_STORY_ID_PREFIX = "SK"
CONFIG_FILENAME = "config.json"

_PREFIX = re.compile(r"^[A-Z][A-Z0-9]*$")


def config_path(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".supskill" / CONFIG_FILENAME


def load_story_id_prefix(root: Path | None = None) -> str:
    """The configured story-id prefix, or DEFAULT_STORY_ID_PREFIX if unset."""
    path = config_path(root)
    if not path.is_file():
        return DEFAULT_STORY_ID_PREFIX
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("story_id_prefix", DEFAULT_STORY_ID_PREFIX)


def write_story_id_prefix(prefix: str, root: Path | None = None) -> None:
    """Validate and persist prefix, preserving any other keys already on disk."""
    if not _PREFIX.match(prefix):
        raise StateError(
            f"--story-id-prefix must be uppercase letters/digits starting with a letter "
            f"(matching {_PREFIX.pattern!r}), got {prefix!r}"
        )
    path = config_path(root)
    data = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    data["story_id_prefix"] = prefix
    store.write_json_config(path, data)
