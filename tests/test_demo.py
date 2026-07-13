"""The sprint demo - the north star in miniature, as one end-to-end CLI test."""

import json
import re
from pathlib import Path

import supskill_state
from supskill_state.cli import main
from supskill_state.model import Stage
from supskill_state.store import gates_path, load_state, state_path


def test_north_star_demo(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    # init s1
    assert main(["init", "s1", "--backlog", "backlog.md"]) == 0

    # SCOPE produced the sprint doc; record it (REFINE refines this same doc in place)
    (tmp_path / "sprint-doc.md").write_text("# sprint doc\n")
    assert main(["artifact", "--set", "sprint_doc", "--path", "sprint-doc.md"]) == 0

    # the REFINE stage happens (no gate guards SCOPE -> REFINE; the recorded doc does)
    assert main(["advance", "--to", "REFINE"]) == 0

    # gate G1: the operator's actual words
    assert main(["gate", "--id", "G1", "--decision", "approved",
                 "--response", "read it - scope grew but it is right. approved."]) == 0

    # advance --to PLAN succeeds
    assert main(["advance", "--to", "PLAN"]) == 0

    # advance --to EXECUTE refuses, loudly, naming G2 - and changes nothing
    before = state_path(tmp_path).read_bytes()
    assert main(["advance", "--to", "EXECUTE"]) == 1
    error = capsys.readouterr().err
    assert "refused" in error and "G2_plan" in error
    assert state_path(tmp_path).read_bytes() == before

    # gates.jsonl shows the whole story in order
    records = [json.loads(line) for line in gates_path(tmp_path).read_text().splitlines()]
    assert [(r["gate"], r["decision"]) for r in records] == [("G1", "approved")]
    assert records[0]["response"] == "read it - scope grew but it is right. approved."

    # kill the process mid-write, then resume from a valid state.json
    (state_path(tmp_path).parent / "state.json.tmp-killed").write_text('{"schema": 1, "back')
    state = load_state(state_path(tmp_path))
    assert state.stage is Stage.PLAN  # the previous valid state, never a truncated one
    assert main(["show"]) == 0
    assert "stage PLAN" in capsys.readouterr().out


def test_no_module_outside_store_opens_files_for_writing():
    # invariant 3, mechanically: store.py is the only module with file-write
    # primitives; every other module goes through store.dump_state/append_jsonl.
    # The authoritative check is the reviewer reading every write site - this
    # test guards the obvious regression.
    package_dir = Path(supskill_state.__file__).parent
    write_call = re.compile(r"""open\([^)]*["'][wax]|\.write_text\(|\.write_bytes\(""")
    offenders = [
        source.name
        for source in package_dir.glob("*.py")
        if source.name != "store.py" and write_call.search(source.read_text(encoding="utf-8"))
    ]
    assert offenders == []
