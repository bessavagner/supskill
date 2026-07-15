"""SK-061: the should-trigger / should-not-trigger corpus is well-formed offline.

The corpus is the one genuinely offline-provable slice of E7. The SCORING is a
live claude -p spend, composed from skill-creator's real loop and run by the
operator (evals/README.md) - NOT reproduced here, and NOT in this suite. What
IS offline and is asserted here: the corpus parses, every entry is well-formed,
both classes are represented, and the should-not-trigger half covers the three
near-miss buckets that matter for a side-effecting conductor (sprint doc,
SK-061 accept criteria): read-only sprint questions, other-repo sprint tooling,
and prompts that name "sprint" without wanting to run one.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPO_ROOT / "evals" / "description-corpus.json"

# The should-not-trigger buckets SK-061's accept criteria name explicitly.
REQUIRED_NEGATIVE_CATEGORIES = {
    "read-only-sprint-question",
    "other-repo-tooling",
    "names-sprint-not-run",
}
# The should-trigger intents the description exists to catch.
REQUIRED_POSITIVE_CATEGORIES = {"start-sprint", "resume-sprint"}


def _corpus() -> list[dict]:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def test_corpus_parses_as_a_nonempty_list():
    corpus = _corpus()
    assert isinstance(corpus, list)
    assert len(corpus) >= 10  # enough for a meaningful trigger rate, both classes


def test_every_entry_is_well_formed_for_skill_creators_consumer():
    for entry in _corpus():
        assert set(entry) >= {"query", "should_trigger", "category"}, entry
        assert isinstance(entry["query"], str) and entry["query"].strip(), entry
        assert isinstance(entry["should_trigger"], bool), entry
        assert isinstance(entry["category"], str) and entry["category"].strip(), entry


def test_both_classes_are_represented():
    flags = {entry["should_trigger"] for entry in _corpus()}
    assert flags == {True, False}


def test_the_positive_half_covers_start_and_resume():
    present = {e["category"] for e in _corpus() if e["should_trigger"]}
    assert REQUIRED_POSITIVE_CATEGORIES <= present, REQUIRED_POSITIVE_CATEGORIES - present


def test_the_negative_half_covers_the_three_side_effecting_near_misses():
    present = {e["category"] for e in _corpus() if not e["should_trigger"]}
    assert REQUIRED_NEGATIVE_CATEGORIES <= present, REQUIRED_NEGATIVE_CATEGORIES - present


def test_queries_are_unique():
    queries = [e["query"] for e in _corpus()]
    assert len(queries) == len(set(queries))
