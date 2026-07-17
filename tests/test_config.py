"""SK-064: per-project story-id prefix config, separate from state.json.

The scheme is a property of the project, not of one sprint run: it must
survive `init --archive` instead of resetting with each sprint, so it lives
in its own file rather than inside state.json.
"""

import json

import pytest

from supskill_state.config import (
    DEFAULT_STORY_ID_PREFIX,
    config_path,
    load_story_id_prefix,
    write_story_id_prefix,
)
from supskill_state.errors import StateError


def test_load_defaults_to_sk_when_no_config_file_exists(tmp_path):
    assert load_story_id_prefix(tmp_path) == "SK" == DEFAULT_STORY_ID_PREFIX


def test_write_then_load_round_trips(tmp_path):
    write_story_id_prefix("BLK", root=tmp_path)
    assert load_story_id_prefix(tmp_path) == "BLK"
    assert config_path(tmp_path).is_file()


def test_config_path_matches_state_jsons_own_supskill_dir(tmp_path):
    assert config_path(tmp_path) == tmp_path / ".supskill" / "config.json"


def test_write_rejects_lowercase_prefix(tmp_path):
    with pytest.raises(StateError, match="story-id-prefix"):
        write_story_id_prefix("blk", root=tmp_path)


def test_write_rejects_digit_first_prefix(tmp_path):
    with pytest.raises(StateError):
        write_story_id_prefix("1BLK", root=tmp_path)


def test_write_rejects_empty_prefix(tmp_path):
    with pytest.raises(StateError):
        write_story_id_prefix("", root=tmp_path)


def test_write_rejects_punctuation_in_prefix(tmp_path):
    with pytest.raises(StateError):
        write_story_id_prefix("BLK-", root=tmp_path)


def test_write_preserves_other_keys_already_in_the_file(tmp_path):
    path = config_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"future_knob": "keep-me"}) + "\n", encoding="utf-8")
    write_story_id_prefix("BLK", root=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"future_knob": "keep-me", "story_id_prefix": "BLK"}


def test_overwriting_the_prefix_updates_in_place(tmp_path):
    write_story_id_prefix("BLK", root=tmp_path)
    write_story_id_prefix("PROJ", root=tmp_path)
    assert load_story_id_prefix(tmp_path) == "PROJ"
