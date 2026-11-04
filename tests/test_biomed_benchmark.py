"""Checks of the BioMedFn benchmark (data/processed/problems_biomed.jsonl, built by 02b_build_biomed.py).

Run:  python3 tests/test_biomed_benchmark.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib import execution as ex  # noqa: E402
from lib.assertions import parse_assertion  # noqa: E402

PROBS = [json.loads(l) for l in open(os.path.join(ROOT, "data", "processed", "problems_biomed.jsonl"))]


def test_structure():
    assert len(PROBS) == 112 and len({p["entry"] for p in PROBS}) == len(PROBS)
    assert {p["domain"] for p in PROBS} == {"clinical", "dosing", "omics", "biosignal"}
    for p in PROBS:
        assert p["ref_src"].startswith(p["spec"]) and p["buggy_src"].startswith(p["spec"]) and p["ref_src"] != p["buggy_src"]
        assert len(p["doc_examples"]) == 2 and len(p["human_io"]) >= 3
        for call, exp in p["doc_examples"]:
            assert parse_assertion(f"assert {call} == {exp}", p["entry"]) is not None


def test_sandbox_agrees_and_faults_are_detected():
    """In the sandbox the reference answers every developer test and the seeded fault changes at least one outcome."""
    for p in PROBS:
        calls = [f"{p['entry']}(*{args!r})" for args, _ in p["human_io"]]
        ref = ex.run_program(p["ref_src"], calls)
        bug = ex.run_program(p["buggy_src"], calls)
        assert all(k != "TIMEOUT" and not k.startswith("LOAD:") for k in ref), p["pid"]
        assert ref != bug, p["pid"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
