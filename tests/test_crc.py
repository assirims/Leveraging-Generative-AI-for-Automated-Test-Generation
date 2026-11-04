"""Tests of the conformal risk control step (06_analysis.crc_from_arrays) and of the committee vote (lib/oracles).

Run:  python3 -m pytest tests   (or: python3 tests/test_crc.py)"""
import importlib.util
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location("analysis", os.path.join(ROOT, "06_analysis.py"))
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)
from lib.oracles import NEG, committee_assertions, plurality  # noqa: E402

INF = float("inf")


def brute_force(ws, grid, alpha):
    """Definition: smallest t in grid with (sum_j 1[w_j >= t] + 1) / (n + 1) <= alpha."""
    n = len(ws)
    for t in sorted(grid):
        if (sum(1 for w in ws if w >= t) + 1) / (n + 1) <= alpha:
            return t
    return INF


def test_crc_matches_definition():
    rng = np.random.default_rng(1)
    for _ in range(400):
        n = int(rng.integers(5, 120))
        ws = rng.choice(np.round(rng.random(30), 2), size=n)
        ws[rng.random(n) < rng.random()] = NEG            # problems without any wrong assertion
        grid = np.array(sorted(set(np.round(rng.random(40), 2)) | set(ws[ws > NEG]) | {INF}))
        for alpha in (0.05, 0.1, 0.2, 0.3):
            assert analysis.crc_from_arrays(ws, grid, alpha) == brute_force(list(ws), list(grid), alpha)


def test_crc_validity_by_simulation():
    """Exchangeable problems: the mean false-alarm rate on new problems must not exceed alpha."""
    rng = np.random.default_rng(2026)
    for alpha in (0.05, 0.1, 0.2):
        losses = []
        for _ in range(4000):
            n = 98
            # w = highest score among the wrong assertions of a problem (NEG: none); scores are informative but imperfect
            w = np.where(rng.random(n + 1) < 0.6, rng.beta(2, 5, n + 1), NEG)
            grid = np.array(sorted(set(np.round(np.linspace(0, 1, 101), 2)) | {INF}))
            t = analysis.crc_from_arrays(w[:n], grid, alpha)
            losses.append(float(w[n] >= t))
        mean = float(np.mean(losses))
        se = math.sqrt(alpha * (1 - alpha) / len(losses))
        assert mean <= alpha + 3 * se, (alpha, mean)


def test_hit_excludes_empty_suites():
    assert not analysis.hit(NEG, NEG) and not analysis.hit(NEG, INF) and analysis.hit(0.5, 0.5) and not analysis.hit(0.4, 0.5)


def test_plurality_tie_break():
    assert plurality(["a", "b", "b", "a"], prefer="b") == ("b", 2)
    assert plurality(["a", "b"], prefer=None) == ("a", 1)


def test_committee_score_and_abstaining_channel():
    ex = {"results": {f"k{i}": ["('n', 1)", "('n', 2)"] for i in range(5)}}
    ex["results"]["k4"] = ["('n', 9)", "('n', 2)"]
    votes = {0: [("('n', 1)", 1.0)]}                         # input 0 has a direct prediction, input 1 does not
    A = committee_assertions(ex, [0, 1], [f"k{i}" for i in range(5)], votes, w=10.0, use_conf=True, n_channels=1)
    s = {i: sc for i, _, sc, _, _ in A}
    assert math.isclose(s[0], 14 / 15) and math.isclose(s[1], 5 / 15)   # amplified input capped at K / (K + w)
    # a confident prediction contradicted by the whole committee scores 10/15 and wins the vote
    ex2 = {"results": {f"k{i}": ["('n', 3)"] for i in range(5)}}
    A2 = committee_assertions(ex2, [0], [f"k{i}" for i in range(5)], {0: [("('n', 1)", 1.0)]}, w=10.0, use_conf=True, n_channels=1)
    assert A2[0][1] == "('n', 1)" and math.isclose(A2[0][2], 10 / 15)


def test_no_assertion_on_exception_plurality():
    ex = {"results": {f"k{i}": ["EXC:ValueError"] for i in range(5)}}
    assert committee_assertions(ex, [0], [f"k{i}" for i in range(5)]) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
