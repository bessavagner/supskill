"""SK-106: refuse at run start when a stage's dispatched skill will not resolve.

supskill composes skills that ship in the `superpowers` plugin: PLAN dispatches
`writing-plans`, EXECUTE dispatches `subagent-driven-development` and invokes its
three scripts by absolute path. plugin.json declares the dependency, and
test_plugin_manifest.py proves the declaration cannot drift — but a *declared*
dependency can still be missing at runtime (install failed, the plugin is
disabled, its marketplace was unreachable). Then a stage dispatches a skill that
does not exist and improvises — the one failure this product exists to prevent.

This is the runtime half. The conductor resolves each still-to-run stage's skills
to a base directory (it loads the skill; the payload's first line is
`Base directory for this skill: <abs path>`) and passes them here. A skill it
could not resolve is simply not passed — and preflight refuses by omission. A
skill it did resolve is checked for the concrete artifacts the stage invokes:
`subagent-driven-development` must carry its three scripts, or EXECUTE dies on a
missing `task-brief` mid-drain. Same shape as the other guards: a pure check
plus a CLI verb that reports and stops. Needs no state file — it is a query.
"""

from __future__ import annotations

from pathlib import Path

from .errors import StateError

STAGE_ORDER: tuple[str, ...] = ("SCOPE", "PLAN", "EXECUTE", "REVIEW")

# The external skill each stage dispatches. SCOPE dispatches none since SK-100
# dropped the pm-execution:sprint-plan dispatch; REVIEW uses supskill's own
# references/review-prompt.md, not an external skill.
STAGE_SKILLS: dict[str, tuple[str, ...]] = {
    "SCOPE": (),
    "PLAN": ("writing-plans",),
    "EXECUTE": ("subagent-driven-development",),
    "REVIEW": (),
}

# The concrete artifacts each skill must carry, relative to its base directory.
# For SDD these are the scripts EXECUTE invokes by absolute path; a missing one
# is a mid-drain crash, so it is a run-start refusal instead.
SKILL_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "writing-plans": ("SKILL.md",),
    "subagent-driven-development": (
        "SKILL.md",
        "scripts/sdd-workspace",
        "scripts/task-brief",
        "scripts/review-package",
    ),
}

_UNRESOLVED = (
    "could not be resolved (not installed, disabled, or its marketplace was unreachable)"
)


def required_skills(stage: str) -> tuple[str, ...]:
    """Every external skill the run may still dispatch from `stage` onward, in order."""
    if stage not in STAGE_ORDER:
        raise StateError(f"unknown stage {stage!r}; expected one of {list(STAGE_ORDER)}")
    skills: list[str] = []
    for later in STAGE_ORDER[STAGE_ORDER.index(stage):]:
        for skill in STAGE_SKILLS[later]:
            if skill not in skills:
                skills.append(skill)
    return tuple(skills)


def unresolved(stage: str, resolved: dict[str, str]) -> list[tuple[str, str]]:
    """(skill, reason) for every required skill that will not resolve.

    `resolved` maps a skill name to the base directory the conductor resolved it
    to. A required skill absent from `resolved` is one the conductor could not
    resolve at all (missing/disabled). A resolved skill missing an expected
    artifact names the missing paths.
    """
    problems: list[tuple[str, str]] = []
    for skill in required_skills(stage):
        base = resolved.get(skill)
        if base is None:
            problems.append((skill, _UNRESOLVED))
            continue
        missing = [rel for rel in SKILL_ARTIFACTS[skill] if not (Path(base) / rel).is_file()]
        if missing:
            problems.append((skill, f"resolved to {base} but is missing: {', '.join(missing)}"))
    return problems


def refusal(stage: str, problems: list[tuple[str, str]]) -> str:
    """What the conductor reports, verbatim, when a required skill will not resolve."""
    if not problems:
        raise StateError("refusal() called with no problems; there is nothing to refuse")
    listed = "\n".join(f"    {skill}: {reason}" for skill, reason in problems)
    return (
        f"a skill a stage from {stage} onward will dispatch does not resolve at run start:\n"
        f"{listed}\n"
        "supskill dispatches these from the `superpowers` plugin (claude-plugins-official). "
        "Install or enable it before running, e.g. "
        "`claude plugin install superpowers@claude-plugins-official`.\n"
        "This run is stopped before the first dispatch: a stage that cannot load the skill it "
        "dispatches improvises, which is the one failure this conductor exists to prevent."
    )
