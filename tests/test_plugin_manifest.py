"""SK-010: the repo is a valid Claude Code plugin - offline invariants.

`claude plugin validate --strict` is the authority; this suite pins the
invariants a validator run cannot be assumed for (CI has no claude binary):
the manifest parses, the name is a legal slug, and components live at the
plugin root, never inside .claude-plugin/ (contexts/02 SS3).
"""

import json
import re
import tomllib
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


def test_nothing_but_the_manifests_live_in_dot_claude_plugin():
    entries = sorted(entry.name for entry in (REPO_ROOT / ".claude-plugin").iterdir())
    assert entries == ["marketplace.json", "plugin.json"]


def test_components_live_at_plugin_root():
    assert (REPO_ROOT / "skills" / "supskill" / "SKILL.md").is_file()
    assert (REPO_ROOT / "agents").is_dir()  # reserved for E3's stage agents
    assert (REPO_ROOT / "scripts" / "supskill-state").is_file()  # untouched where S1 put it


# --- SK-060: the composed skills are declared, and the declaration cannot drift ---
#
# supskill dispatches skills that ship in OTHER plugins. Undeclared, a fresh
# install resolves none of them and a stage dispatches a skill that does not
# exist -- which does not crash, it improvises. Silent guessing at a stage
# boundary is the one failure this product exists to prevent, so the mapping
# from "skill the conductor dispatches" to "plugin declared as a dependency"
# is asserted, not documented.
#
# Both dependencies are CROSS-marketplace, which Claude Code blocks by default;
# marketplace.json's allowCrossMarketplaceDependenciesOn is what unblocks them.
#
# Deliberately unversioned: constraints resolve against `{plugin}--v{version}`
# git tags on the dependency's marketplace repo, and NEITHER upstream tags that
# way (verified: 0 matching tags on anthropics/claude-plugins-official and
# phuryn/pm-skills). A version constraint would resolve to no-matching-tag and
# Claude Code would DISABLE supskill. Pin only once upstream tags releases.

SKILL_NAMESPACE = re.compile(r"\b([a-z0-9-]+):([a-z0-9-]+)\b")

# Skills the conductor dispatches, and the plugin that ships each.
DISPATCHED_SKILL_PLUGINS = {
    "superpowers": "superpowers",
}


def _declared_dependencies() -> dict[str, str]:
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    declared = {}
    for entry in raw.get("dependencies", []):
        if isinstance(entry, str):
            declared[entry] = ""
        else:
            declared[entry["name"]] = entry.get("marketplace", "")
    return declared


def _skill_namespaces_dispatched() -> set[str]:
    """Every `<plugin-namespace>:<skill>` token the conductor's prompts dispatch."""
    found = set()
    for path in (REPO_ROOT / "skills").rglob("*.md"):
        for namespace, _skill in SKILL_NAMESPACE.findall(path.read_text(encoding="utf-8")):
            if namespace in DISPATCHED_SKILL_PLUGINS:
                found.add(namespace)
    return found


def test_every_dispatched_skill_has_its_plugin_declared_as_a_dependency():
    declared = _declared_dependencies()
    dispatched = _skill_namespaces_dispatched()
    # Not decoration: over an empty set the loop below passes vacuously, and the
    # test would keep reporting green after a refactor moved the prompts.
    assert dispatched, "found no dispatched external skills in skills/ -- the scan is broken"
    for namespace in dispatched:
        plugin = DISPATCHED_SKILL_PLUGINS[namespace]
        assert plugin in declared, (
            f"skills/ dispatches `{namespace}:...` but plugin '{plugin}' is not in "
            f"plugin.json dependencies -- a fresh install would resolve nothing and "
            f"the stage would improvise"
        )


def test_cross_marketplace_dependencies_are_allowlisted():
    """A dependency naming another marketplace fails to install unless the root
    marketplace allows that marketplace by name."""
    marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    allowed = set(marketplace.get("allowCrossMarketplaceDependenciesOn", []))
    for name, source in _declared_dependencies().items():
        if source:
            assert source in allowed, (
                f"dependency '{name}' resolves in marketplace '{source}', which is absent from "
                f"allowCrossMarketplaceDependenciesOn -- install fails with a cross-marketplace error"
            )


def test_dependencies_are_unversioned_while_upstream_ships_no_tags():
    """Guards the footgun: a semver range with no matching `{plugin}--v*` tag
    upstream resolves to no-matching-tag and DISABLES supskill. Remove this test
    the day the dependency's marketplace starts tagging releases."""
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in raw.get("dependencies", []):
        if isinstance(entry, dict):
            assert "version" not in entry, (
                f"dependency '{entry['name']}' declares a version constraint, but constraints "
                f"resolve against {entry['name']}--v* git tags that its marketplace does not publish"
            )


def test_marketplace_lists_this_plugin():
    marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert marketplace["name"]
    assert marketplace["owner"]["name"]
    names = [plugin["name"] for plugin in marketplace["plugins"]]
    assert json.loads(MANIFEST.read_text(encoding="utf-8"))["name"] in names


def test_plugin_version_matches_pyproject_so_the_release_tag_is_consistent():
    # SK-060: the v0.1.0 tag is cut from pyproject's version (release hygiene,
    # DoR finding 4 - NOT what install resolves against). Keep the manifest's
    # own version equal to it so the tag never names a version they disagree on.
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["version"] == pyproject["project"]["version"]


def test_skill_creator_is_not_a_runtime_dependency():
    # SK-061, DoR finding 6: skill-creator is an author/eval-time tool composed
    # by evals/README.md's loop - the conductor never dispatches it. It must stay
    # out of both the dispatched-skill set and the declared runtime dependencies,
    # or the declaration guard above would demand a manifest entry for a tool no
    # stage dispatches and pull a third cross-marketplace dep into the install.
    assert "skill-creator" not in DISPATCHED_SKILL_PLUGINS
    assert "skill-creator" not in _declared_dependencies()
