# Invocation model — decided at S2 (SK-011)

**Decision:** v1 of the `supskill` skill is user-invoked only —
`disable-model-invocation: true` in the SKILL.md frontmatter.

**Why.** The conductor is side-effecting: it spawns subagents, spends tokens,
and mutates the operator's repository (`.supskill/`, sprint branches, recorded
artifacts). contexts/02's implication #2 applies directly: skills with side
effects the user should control the timing of do not belong on default
auto-invoke. The operator decides when a sprint starts or resumes; the model
does not.

**The flagged tension (E7 revisits).** SK-061's should-trigger /
should-not-trigger eval loop mostly exercises auto-invocation — the very path
this flag disables. Until E7, those evals would measure a hypothetical. E7
either relaxes the flag with eval evidence in hand, or re-scopes SK-061 to
user-invocation UX (argument parsing, wrong-repo refusals). Recorded here so
E7 inherits the tension explicitly instead of rediscovering it.
