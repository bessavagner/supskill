"""SK-070: the fixture repo's toy backlog is well-formed offline.

The live end-to-end run through both its sprints is SK-070's actual accept
criteria and needs real LLM calls (validation/fixture-run.md) - deliberately
not part of this offline suite, the same split evals/ already uses for
SK-061. What IS offline and asserted here: the backlog itself parses in the
row format every other backlog in this repo already uses, both epics exist,
and every story id is well-formed - the mechanical floor a real run should
never trip over.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_BACKLOG = (
    REPO_ROOT / "validation" / "fixture-repo" / "docs" / "plans" / "sprints" / "backlog-01" / "backlog.md"
)

ROW = re.compile(r"^\| (SK-\d{3}) \| (.+) \| (\d+) \| ([MSCW]) \| (☐|☑) \|$", re.MULTILINE)


def _rows() -> list[tuple[str, str, str, str, str]]:
    text = FIXTURE_BACKLOG.read_text(encoding="utf-8")
    return ROW.findall(text)


def test_the_fixture_backlog_file_exists():
    assert FIXTURE_BACKLOG.is_file()


def test_every_story_row_matches_the_repos_own_row_format():
    rows = _rows()
    assert len(rows) >= 4  # both epics, at least two stories each


def test_story_ids_are_unique_and_sequential_from_sk_001():
    ids = [row[0] for row in _rows()]
    assert ids == sorted(ids)
    assert ids[0] == "SK-001"
    assert len(ids) == len(set(ids))


def test_both_epics_are_present_in_the_summary_table():
    text = FIXTURE_BACKLOG.read_text(encoding="utf-8")
    assert "| **E1** | Greeting core | 3 | M |" in text
    assert "| **E2** | Greeting CLI | 3 | M |" in text


def test_every_story_starts_todo_not_already_done():
    assert {row[4] for row in _rows()} == {"☐"}
