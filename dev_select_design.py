"""Design selection on the development model (Qwen2.5-0.5B) only.

Before the 1.5B and 3B models were evaluated, the CORAL score was fixed by comparing a small set of variants on the
outputs of the development model: the weight of the direct-prediction vote (w), whether that vote is weighted by the
token confidence, and whether amplified inputs must be informative (distinguish at least one mutant of the model's own
greedy implementation). Criterion: mean mutation score on the test halves of random calibration/test splits at
alpha = 0.10 and 0.20 (the false-alarm rate is controlled by construction). Output: results/tables/dev_design_selection.csv
"""
import importlib.util
import os
import random

import numpy as np
import pandas as pd

from config import DEV_SPLITS, PROC, SEED, SUITE, TABLES
from lib.oracles import committee_assertions, direct_assertions, direct_votes, faulty_programs, informative_inputs, inputs_of, summarise

spec = importlib.util.spec_from_file_location("an", os.path.join(os.path.dirname(os.path.abspath(__file__)), "06_analysis.py"))
an = importlib.util.module_from_spec(spec)
spec.loader.exec_module(an)

DEV = "qwen0.5b"
VARIANTS = {
    "w = 1": dict(w=1.0, use_conf=False, info=False, fixed=False),
    "w = 1, confidence-weighted": dict(w=1.0, use_conf=True, info=False, fixed=False),
    "w = 3, confidence-weighted": dict(w=3.0, use_conf=True, info=False, fixed=False),
    "w = K, confidence-weighted": dict(w=5.0, use_conf=True, info=False, fixed=False),
    "w = 1, confidence-weighted, abstaining channel": dict(w=1.0, use_conf=True, info=False, fixed=True),
    "w = 3, confidence-weighted, abstaining channel": dict(w=3.0, use_conf=True, info=False, fixed=True),
    "w = K, abstaining channel": dict(w=5.0, use_conf=False, info=False, fixed=True),
    "w = K, confidence-weighted, abstaining channel": dict(w=5.0, use_conf=True, info=False, fixed=True),
    "w = K, confidence-weighted, abstaining channel, informative": dict(w=5.0, use_conf=True, info=True, fixed=True),
    "w = 2K, confidence-weighted, abstaining channel (selected)": dict(w=10.0, use_conf=True, info=False, fixed=True),
}


def main():
    if SUITE != "general":
        print("design selection uses the general suite only; nothing to do for", SUITE)
        return
    EX = [e for e in an.load() if DEV in e["direct"]]
    P = []
    for ex in EX:
        f = faulty_programs(ex)
        XA = inputs_of(ex, [DEV])
        X = set(inputs_of(ex, [DEV], ("llm",)))
        mem = [f"{DEV}_k{j}" for j in range(5)]
        dv = direct_votes(ex, [DEV])
        summ = {"Direct+conf": summarise(ex, direct_assertions(ex, [DEV], "conf"), f)}
        for name, v in VARIANTS.items():
            allowed = None
            if v["info"]:
                allowed = X | informative_inputs(ex, DEV, XA)
            summ[name] = summarise(ex, committee_assertions(ex, XA, mem, dv, v["w"], v["use_conf"], allowed, 1 if v["fixed"] else None), f)
        P.append({"pid": ex["pid"], "bench": ex["bench"], "faulty": f, "summ": summ})
    rng = random.Random(SEED + 7)
    rows = []
    AR = {m: an.Arrays(P, m) for m in ["Direct+conf"] + list(VARIANTS)}
    for s in range(DEV_SPLITS):
        idx = list(range(len(P)))
        rng.shuffle(idx)
        cal = set(idx[: len(P) // 2])
        for m, ar in AR.items():
            cm = np.array([i in cal for i in ar.idx])
            for a in (0.1, 0.2):
                t = an.crc_from_arrays(ar.w[cm], ar.grid(cm), a)
                r = ar.metrics(~cm, t)
                r.update({"variant": m, "alpha": a})
                rows.append(r)
    R = pd.DataFrame(rows).groupby(["variant", "alpha"])[["fa", "mut_score", "asserts", "det_llm", "det_real"]].mean().reset_index()
    R.to_csv(os.path.join(TABLES, "dev_design_selection.csv"), index=False)
    print(f"development model {DEV}: {len(P)} problems")
    print(R.round(3).to_string())


if __name__ == "__main__":
    main()
