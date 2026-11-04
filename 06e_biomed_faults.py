"""Step 6e (biomedical suite) - detection of the seeded domain faults by fault category and by biomedical domain.

Uses the cross-fitted thresholds of step 6 (data/processed/biomed/xfit_thresholds.json): every problem's suite is
admitted with a threshold calibrated on the other half of the problems. A domain fault is detected if at least one
admitted correct assertion fails on it. Output: results/tables/biomed/fault_category_detection.csv
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import PROBLEMS_FILE, PROC_OUT, SUITE, TABLES  # noqa: E402

spec = importlib.util.spec_from_file_location("analysis", os.path.join(HERE, "06_analysis.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def main():
    assert SUITE == "biomed", "run with CORAL_SUITE=biomed"
    cat = {json.loads(l)["pid"]: json.loads(l)["fault_category"] for l in open(PROBLEMS_FILE)}
    EX = A.load()
    models = A.models_in(EX)
    P = A.problem_tables(EX, models)
    X = json.load(open(os.path.join(PROC_OUT, "xfit_thresholds.json")))
    specs = [("Developer tests", None), ("Doctest", None)]
    for m in models:
        specs += [(f"Direct|{m}", None), (f"Direct+conf|{m}", 0.1), (f"CORAL|{m}", 0.1)]
    specs += [("CORAL-hetero", 0.1)]
    rows = []
    for meth, a in specs:
        th = X.get(f"{meth}@{a}") if a is not None else None
        for p in P:
            s = p["summ"].get(meth)
            if s is None:
                continue
            t = -A.INF if th is None else th[p["pid"]]
            for b, cls in p["faulty"].items():
                if cls == "real":
                    rows.append({"method": meth, "alpha": a, "pid": p["pid"], "domain": p["group"], "category": cat[p["pid"]],
                                 "detected": int(A.hit(s["det"].get(b, A.NEG), t))})
    D = pd.DataFrame(rows)
    out = []
    for (meth, a), g in D.groupby(["method", "alpha"], dropna=False):
        for key, col in (("category", "category"), ("domain", "domain")):
            for v, h in g.groupby(col):
                out.append({"method": meth, "alpha": a, "by": key, "level": v, "n": len(h), "detected": int(h.detected.sum()),
                            "share": float(h.detected.mean())})
        out.append({"method": meth, "alpha": a, "by": "all", "level": "all", "n": len(g), "detected": int(g.detected.sum()),
                    "share": float(g.detected.mean())})
    T = pd.DataFrame(out)
    T.to_csv(os.path.join(TABLES, "fault_category_detection.csv"), index=False)
    print(T[T.by != "domain"].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
