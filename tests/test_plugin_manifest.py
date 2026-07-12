"""SK-010: the repo is a valid Claude Code plugin - offline invariants.

`claude plugin validate --strict` is the authority; this suite pins the
invariants a validator run cannot be assumed for (CI has no claude binary):
the manifest parses, the name is a legal slug, and components live at the
plugin root, never inside .claude-plugin/ (contexts/02 SS3).
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"

KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_manifest_parses_as_json():
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)


def test_plugin_name_is_a_legal_slug():
    name = json.loads(MANIFEST.read_text(encoding="utf-8"))["name"]
    assert name == "supskill"  # working title; the slug freeze is SK-060's decision
    assert len(name) <= 64
    assert KEBAB_CASE.fullmatch(name)
    assert "claude" not in name and "anthropic" not in name


def test_manifest_carries_version_description_author():
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert raw["version"]
    assert raw["description"]
    assert raw["author"]["name"]


def test_nothing_but_the_manifest_lives_in_dot_claude_plugin():
    entries = sorted(entry.name for entry in (REPO_ROOT / ".claude-plugin").iterdir())
    assert entries == ["plugin.json"]


def test_components_live_at_plugin_root():
    assert (REPO_ROOT / "skills" / "supskill" / "SKILL.md").is_file()
    assert (REPO_ROOT / "agents").is_dir()  # reserved for E3's stage agents
    assert (REPO_ROOT / "scripts" / "supskill-state").is_file()  # untouched where S1 put it
