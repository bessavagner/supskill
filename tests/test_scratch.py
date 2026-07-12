"""SK-004: scratch paths are derived from the sprint id; collisions are impossible."""

import pytest

from supskill_state.errors import StateError
from supskill_state.scratch import derive_scratch, normalize_sprint_id


def test_s9a_scratch_path_differs_from_s9():
    # the design's own named test (design decisions, section 6)
    assert derive_scratch("S9a") != derive_scratch("S9")


def test_path_shape():
    assert derive_scratch("S10") == ".superpowers/sdd/s10/"


def test_case_variants_are_the_same_sprint():
    assert derive_scratch("S9") == derive_scratch("s9")
    assert normalize_sprint_id("SPRINT-01") == "sprint-01"


@pytest.mark.parametrize(
    "bad_id",
    ["s9_a", "s 9", "s9/../s10", "", "S9.A", "sprint#1", "s9é", ".", "s9/"],
)
def test_ids_that_will_not_normalize_cleanly_are_rejected_never_mangled(bad_id):
    with pytest.raises(StateError, match="refusing"):
        normalize_sprint_id(bad_id)


def test_distinct_normalized_ids_always_yield_distinct_paths():
    # property-style: derive over a broad id sample; distinct normal forms -> distinct paths
    ids = (
        [f"s{n}" for n in range(60)]
        + [f"s{n}a" for n in range(60)]
        + [f"sprint-{n:02d}" for n in range(30)]
        + ["backlog-02-s3", "s9b", "e1-state-spine"]
    )
    normalized = [normalize_sprint_id(i) for i in ids]
    paths = [derive_scratch(i) for i in ids]
    assert len(set(paths)) == len(set(normalized)) == len(ids)
