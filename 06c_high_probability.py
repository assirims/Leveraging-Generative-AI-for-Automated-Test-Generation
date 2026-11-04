"""Step 6c - high-probability false-alarm control (Learn-then-Test) compared with conformal risk control.

Conformal risk control (CRC, step 6) bounds the false-alarm rate in expectation over calibration samples, so that a
single calibration sample can still give a threshold whose false-alarm rate exceeds alpha. Learn-then-Test (LTT;
Angelopoulos et al., Ann. Appl. Stat. 2025) gives the stronger guarantee P(R(t_hat) <= alpha) >= 1 - delta over
calibration samples. For the binary false-alarm loss the null hypothesis H_t: R(t) > alpha is tested with the exact
binomial p-value p(t) = P(Binom(n, alpha) <= k(t)), where k(t) is the number of calibration problems whose suite at
threshold t fails on the correct reference. Because k(t) can only grow when t decreases, fixed-sequence testing from
the empty suite (t = +inf) downwards selects the smallest threshold t with p(t) <= delta.

Both procedures are applied to the same random calibration/test splits of all problems.
Outputs: results/tables[/biomed]/high_probability.csv (summary), data/processed[/biomed]/hp_splits.csv (per split).
"""
import importlib.util
import math
import os
import random
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import ALPHAS, N_SPLITS, PROC_OUT, SEED, TABLES  # noqa: E402

spec = importlib.util.spec_from_file_location("analysis", os.path.join(HERE, "06_analysis.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
NEG, INF = A.NEG, A.INF

DELTA = 0.10
SEED_HP = SEED + 11


def ltt_from_arrays(ws, grid, alpha, delta=DELTA):
    """Smallest grid threshold t with P(Binom(n, alpha) <= k(t)) <= delta, k(t) = #{j : w_j >= t} (fixed sequence)."""
    n = len(ws)
    kmax = -1
    for k in range(n + 1):                       # largest admissible number of calibration false alarms
        if stats.binom.cdf(k, n, alpha) <= delta:
            kmax = k
        else:
            break
    if kmax < 0:
        return INF, kmax
    fin = np.sort(ws[ws > NEG])[::-1]
    if len(fin) <= kmax:
        return float(grid[0]), kmax
    j = np.searchsorted(grid, fin[kmax], side="right")
    return (float(grid[j]) if j < len(grid) else INF), kmax


def main():
    EX = A.load()
    models = A.models_in(EX)
    P = A.problem_tables(EX, models)
    methods = [f"CORAL|{m}" for m in models] + [f"Direct+conf|{m}" for m in models] + ["CORAL-hetero"]
    methods = [m for m in methods if any(m in p["summ"] for p in P)]
    AR = {m: A.Arrays(P, m) for m in methods}
    rng = random.Random(SEED_HP)
    rows = []
    for s in range(N_SPLITS):
        idx = list(range(len(P)))
        rng.shuffle(idx)
        cal_set = set(idx[: len(idx) // 2])
        for m in methods:
            ar = AR[m]
            cal = np.array([i in cal_set for i in ar.idx])
            grid = ar.grid(cal)
            for a in ALPHAS:
                n = int(cal.sum())
                k_crc = math.floor((n + 1) * a - 1 + 1e-12)
                t_crc = A.crc_from_arrays(ar.w[cal], grid, a)
                t_ltt, k_ltt = ltt_from_arrays(ar.w[cal], grid, a)
                for proc, t, k in (("CRC", t_crc, k_crc), ("LTT", t_ltt, k_ltt)):
                    r = ar.metrics(~cal, t)
                    r.update({"method": m, "alpha": a, "procedure": proc, "split": s, "t": t, "k_allowed": k, "n_cal": n})
                    rows.append(r)
    S = pd.DataFrame(rows)
    os.makedirs(PROC_OUT, exist_ok=True)
    S.to_csv(os.path.join(PROC_OUT, "hp_splits.csv"), index=False)
    out = []
    for (m, a, proc), g in S.groupby(["method", "alpha", "procedure"]):
        out.append({"method": m, "alpha": a, "procedure": proc, "delta": DELTA if proc == "LTT" else None,
                    "n_splits": len(g), "n_cal_median": float(g.n_cal.median()), "k_allowed_median": float(g.k_allowed.median()),
                    "fa_mean": float(g.fa.mean()), "fa_sd": float(g.fa.std()), "fa_q90": float(g.fa.quantile(0.9)),
                    "share_ok": float(np.mean(g.fa <= a + 1e-12)), "asserts": float(g.asserts.mean()),
                    "det_real": float(g.det_real.mean()), "det_llm": float(g.det_llm.mean()), "mut_score": float(g.mut_score.mean()),
                    "empty_share": float(np.mean(np.isinf(g.t))), "t_median": float(g.t.median())})
    T = pd.DataFrame(out)
    # paired comparison of LTT with CRC on the same splits: share of splits in which the false-alarm rate exceeds alpha
    for i, r in T.iterrows():
        g = S[(S.method == r.method) & (S.alpha == r.alpha)]
        c = g[g.procedure == "CRC"].set_index("split").fa > r.alpha + 1e-12
        l = g[g.procedure == "LTT"].set_index("split").fa > r.alpha + 1e-12
        T.loc[i, "exceed_crc_only"] = int((c & ~l).sum())
        T.loc[i, "exceed_ltt_only"] = int((l & ~c).sum())
    T.to_csv(os.path.join(TABLES, "high_probability.csv"), index=False)
    pd.set_option("display.width", 200)
    print(f"Learn-then-Test (delta = {DELTA}) versus conformal risk control, {N_SPLITS} random splits of {len(P)} problems")
    print(T[["method", "alpha", "procedure", "k_allowed_median", "fa_mean", "fa_q90", "share_ok", "asserts", "det_real", "det_llm",
             "mut_score", "empty_share"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
