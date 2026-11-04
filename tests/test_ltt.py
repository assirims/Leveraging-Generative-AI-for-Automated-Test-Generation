"""Tests of the high-probability admission step (06c_high_probability.ltt_from_arrays, Learn-then-Test).

Run:  python3 -m pytest tests   (or: python3 tests/test_ltt.py)"""
import importlib.util
import os
import sys

import numpy as np
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location("hp", os.path.join(ROOT, "06c_high_probability.py"))
hp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hp)
NEG, INF = hp.NEG, hp.INF


def brute_force(ws, grid, alpha, delta):
    """Definition: fixed-sequence testing from the largest threshold downwards with the binomial p-value
    p(t) = P(Binom(n, alpha) <= k(t)); returns the last threshold before the first non-rejection."""
    n, last = len(ws), INF
    for t in sorted(grid, reverse=True):
        k = sum(1 for w in ws if w > NEG and w >= t)
        if stats.binom.cdf(k, n, alpha) <= delta:
            last = t
        else:
            break
    return last


def test_ltt_matches_definition():
    rng = np.random.default_rng(3)
    for _ in range(300):
        n = int(rng.integers(10, 120))
        ws = rng.choice(np.round(rng.random(30), 2), size=n)
        ws[rng.random(n) < rng.random()] = NEG
        grid = np.array(sorted(set(np.round(rng.random(40), 2)) | set(ws[ws > NEG]) | {INF}))
        for alpha in (0.05, 0.1, 0.2):
            t, _ = hp.ltt_from_arrays(ws, grid, alpha, 0.1)
            assert t == brute_force(list(ws), list(grid), alpha, 0.1)


def test_ltt_is_more_conservative_than_crc():
    rng = np.random.default_rng(4)
    for _ in range(200):
        n = 97
        ws = np.where(rng.random(n) < 0.6, rng.beta(2, 5, n), NEG)
        grid = np.array(sorted(set(np.round(np.linspace(0, 1, 101), 2)) | {INF}))
        for alpha in (0.05, 0.1, 0.2):
            assert hp.ltt_from_arrays(ws, grid, alpha, 0.1)[0] >= hp.A.crc_from_arrays(ws, grid, alpha)


def test_ltt_high_probability_validity_by_simulation():
    """i.i.d. problems: the true risk R(t_hat) = P(w >= t_hat) must exceed alpha in at most a share delta of calibrations."""
    rng = np.random.default_rng(2026)
    delta = 0.1
    grid = np.array(sorted(set(np.round(np.linspace(0, 1, 201), 3)) | {INF}))
    p_wrong = 0.6                                            # share of problems with at least one wrong assertion
    risk = lambda t: 0.0 if np.isinf(t) else p_wrong * (1 - stats.beta.cdf(t, 2, 5))
    for alpha in (0.05, 0.1, 0.2):
        bad = 0
        reps = 3000
        for _ in range(reps):
            w = np.where(rng.random(97) < p_wrong, rng.beta(2, 5, 97), NEG)
            t, _ = hp.ltt_from_arrays(w, grid, alpha, delta)
            bad += risk(t) > alpha
        share = bad / reps
        se = (delta * (1 - delta) / reps) ** 0.5
        assert share <= delta + 3 * se, (alpha, share)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
