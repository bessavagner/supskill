"""Plan-time discovery: recording stage artifacts, the field advance's preconditions read."""

import pytest

from supskill_state.cli import main
from supskill_state.commands import init_sprint, record_artifact
from supskill_state.errors import StateError
from supskill_state.store import load_state, state_path


def test_artifact_records_the_path(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    (tmp_path / "sprint-doc.md").write_text("# sprint doc\n")
    state = record_artifact("sprint_doc", "sprint-doc.md", root=tmp_path)
    assert state.artifacts["sprint_doc"] == "sprint-doc.md"
    assert load_state(state_path(tmp_path)).artifacts["sprint_doc"] == "sprint-doc.md"


def test_artifact_unknown_name_refused(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    (tmp_path / "x.md").write_text("x")
    with pytest.raises(StateError, match="unknown artifact"):
        record_artifact("review_doc", "x.md", root=tmp_path)


def test_artifact_missing_file_refused_and_state_untouched(tmp_path):
    init_sprint("s1", backlog="backlog.md", root=tmp_path)
    before = state_path(tmp_path).read_bytes()
    with pytest.raises(StateError, match="not found"):
        record_artifact("sprint_doc", "no-such-file.md", root=tmp_path)
    assert state_path(tmp_path).read_bytes() == before


def test_artifact_requires_an_initialized_sprint(tmp_path):
    (tmp_path / "doc.md").write_text("x")
    with pytest.raises(StateError, match="init"):
        record_artifact("sprint_doc", "doc.md", root=tmp_path)


def test_cli_artifact(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "s1", "--backlog", "backlog.md"]) == 0
    (tmp_path / "doc.md").write_text("x")
    assert main(["artifact", "--set", "sprint_doc", "--path", "doc.md"]) == 0
    assert main(["artifact", "--set", "sprint_doc", "--path", "missing.md"]) == 1
    assert "refused" in capsys.readouterr().err
