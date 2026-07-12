"""SK-011: the skill's frontmatter obeys every hard limit, loudly.

Malformed frontmatter YAML still loads the skill but with NO description, so
it never auto-triggers and only --debug shows why (contexts/02 SS1). This
suite is the CI step that makes that silent failure mode loud, and pins the
hard numbers: name <=64 kebab-case without reserved words, description
non-empty <=1024, combined description + when_to_use <=1536, body <=500 lines.

The no-workflow-summary property is reviewer judgment, not regex (sprint risk
table says so honestly); WORKFLOW_TOKENS below is only a tripwire for the
obvious regression - a stage or gate name appearing in the description.
"""

import re
from pathlib import Path

import pytest
import yaml

SKILL = Path(__file__).resolve().parent.parent / "skills" / "supskill" / "SKILL.md"

KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
XML_TAG = re.compile(r"<[^>]+>")
WORKFLOW_TOKENS = re.compile(r"\b(SCOPE|REFINE|PLAN|EXECUTE|REVIEW|G1|G2|G3)\b")


def read_frontmatter_and_body() -> tuple[dict, list[str]]:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must open with a frontmatter block"
    closing = text.index("\n---\n", 4)
    parsed = yaml.safe_load(text[4:closing])  # yaml.YAMLError here IS the loud failure
    assert isinstance(parsed, dict), "frontmatter must parse as a YAML mapping"
    body = text[closing + len("\n---\n"):].splitlines()
    return parsed, body


@pytest.fixture(scope="module")
def frontmatter() -> dict:
    return read_frontmatter_and_body()[0]


def test_name_is_explicit_and_legal(frontmatter):
    name = frontmatter["name"]
    assert name == "supskill"
    assert len(name) <= 64
    assert KEBAB_CASE.fullmatch(name)
    assert "claude" not in name and "anthropic" not in name
    assert not XML_TAG.search(name)


def test_description_states_triggering_conditions_within_limits(frontmatter):
    description = frontmatter["description"]
    assert isinstance(description, str) and description.strip()
    assert len(description) <= 1024
    assert not XML_TAG.search(description)
    assert not WORKFLOW_TOKENS.search(description), (
        "a stage or gate name in the description is the documented regression's tripwire"
    )


def test_combined_trigger_text_fits_the_rendered_cap(frontmatter):
    combined = frontmatter["description"] + frontmatter.get("when_to_use", "")
    assert len(combined) <= 1536


def test_conductor_is_user_invoked_only(frontmatter):
    # side-effecting skill: spawns subagents, spends tokens, mutates the repo
    assert frontmatter["disable-model-invocation"] is True


def test_argument_hint_names_the_verb(frontmatter):
    assert frontmatter["argument-hint"] == "run <sprint-id>"


def test_body_stays_under_500_lines():
    _, body = read_frontmatter_and_body()
    assert len(body) <= 500


def test_invocation_model_reference_is_one_hop_from_the_skill():
    reference = SKILL.parent / "references" / "invocation-model.md"
    assert reference.is_file()
    assert "references/invocation-model.md" in SKILL.read_text(encoding="utf-8")
