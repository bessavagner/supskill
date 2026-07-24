# supskill runbook

Operator procedures for this repo — the things you run rarely enough to forget.
Copy-paste as written; every command shows what it prints and how it fails.

The README's Quickstart covers getting the stack running. This file covers
operating it afterwards.

- [Cut a release](#cut-a-release)
- [Update the installed plugin to a new release](#update-the-installed-plugin-to-a-new-release)
- [Check which version is actually running](#check-which-version-is-actually-running)

---

## Cut a release

Three files carry the version and a test refuses to let them disagree
(`tests/test_plugin_manifest.py::test_plugin_version_matches_pyproject_so_the_release_tag_is_consistent`).
Bump all three, tag, push both the branch and the tag.

Replace `0.6.0` with the version you are cutting.

```bash
# 1. bump both manifests to the SAME version
sed -i 's/^version = "0.5.0"$/version = "0.6.0"/' pyproject.toml
sed -i 's/"version": "0.5.0",/"version": "0.6.0",/' .claude-plugin/plugin.json

# 2. re-lock so uv.lock follows — this is the step that gets forgotten
uv lock

# 3. prove it before tagging
uv run pytest && uv run ruff check .

# 4. commit, tag, push both
git add pyproject.toml .claude-plugin/plugin.json uv.lock
git commit -m "chore: release 0.6.0 — <headline>"
git tag -a v0.6.0 -m "supskill 0.6.0 — <headline>"
git push origin main
git push origin v0.6.0
```

`uv lock` prints the line that confirms it did its job:

```
Resolved 9 packages in 103ms
Updated supskill v0.5.0 -> v0.6.0
```

`git push origin v0.6.0` prints `* [new tag]  v0.6.0 -> v0.6.0`.

**The common failure: skipping `uv lock`.** `uv.lock` pins the project's own
version too, so it silently keeps the old number and the release commit ships a
lockfile that disagrees with both manifests. This happened after 0.3.0 and cost a
separate repair commit. The test suite does *not* catch it — the version guard
compares `pyproject.toml` against `.claude-plugin/plugin.json` only.

**The other one: releasing what you have not pushed.** The tag is a marker for
humans; installs track `main`'s HEAD (see below). A tag pushed without its branch
releases nothing.

Commit message convention: `chore: release X.Y.Z — <headline>`, body naming each
story that ships and whether the schema changed (an in-progress sprint has to know
whether it can resume across the upgrade). See `git log v0.4.0 v0.5.0` for the shape.

---

## Update the installed plugin to a new release

**Releasing does not update your own install.** `/supskill run` executes whatever
version sits in the plugin cache, so until you run this, a dogfood run exercises
the *old* code and the fixes you just shipped are not under test.

```bash
# 1. refresh the marketplace clone from GitHub — WITHOUT this, step 2 sees a
#    stale clone and reports there is nothing to update
claude plugin marketplace update supskill

# 2. update the plugin itself
claude plugin update supskill@supskill
```

Then **restart Claude Code** — `claude plugin update` says so itself
(`restart required to apply`). A running session keeps the old code loaded.

Verify a new cache directory appeared for the version you expect:

```bash
ls ~/.claude/plugins/cache/supskill/supskill/
```

```
0.1.0  0.2.0  0.2.1  0.3.0  0.4.0  0.5.0
```

Old version directories are kept, so the presence of the *newest* one is the
signal — not the count.

**The install tracks `main`'s HEAD, not the `vX.Y.Z` tag.** The marketplace source
is the GitHub repo (`bessavagner/supskill`), and the recorded `gitCommitSha` in
`~/.claude/plugins/installed_plugins.json` is whatever `main` pointed at when you
updated — after the 0.4.0 release that was `1f1a6da` (the handoff commit), not
`00b9dd2` (the tagged release commit). Two consequences:

- push `main` before updating, or you pull a version that does not exist yet;
- a commit landing on `main` after the release commit is picked up as that same
  version — the version number reflects `plugin.json`, not the tag.

**The common failure: `update` reports "already up to date" right after a release.**
The marketplace clone under `~/.claude/plugins/marketplaces/supskill` is a separate
checkout with its own fetch time. Run step 1 first, always.

---

## Check which version is actually running

Between "released", "installed" and "loaded in this session" there are three
different answers. This prints the installed one, which is the one that matters
for a dogfood run:

```bash
python3 -c "
import json, pathlib
d = json.loads((pathlib.Path.home() / '.claude/plugins/installed_plugins.json').read_text())
for rec in d['plugins']['supskill@supskill']:
    print(rec['version'], rec['installPath'], rec['gitCommitSha'][:7], rec['lastUpdated'])
"
```

```
0.5.0 /home/bessa/.claude/plugins/cache/supskill/supskill/0.5.0 6f376eb 2026-07-24T...
```

Cross-check the released version with `git describe --tags --abbrev=0` in this
repo. If the two disagree, the install is stale and the next run is testing old
code — that is the whole reason this section exists.
