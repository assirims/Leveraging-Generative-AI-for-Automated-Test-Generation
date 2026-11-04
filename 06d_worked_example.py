"""Step 6d - worked example: the assertions of the evaluation model for one problem, with the committee votes, the CORAL
score, the reference outcome and the admission decision at the median calibrated thresholds (alpha = 0.10).

General suite: HumanEval/0 (fixed in advance). Biomedical suite: the first BioMedFn problem in benchmark order for which
the evaluation model wrote at least one wrong expected value with token probability >= 0.9 and at least one correct
one (a selection rule fixed before the biomedical results were seen; the example is illustrative, not a result).
Output: results/tables[/biomed]/worked_example.csv
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import K_IMPL, SUITE, TABLES, W_DIRECT, read_executions  # noqa: E402
from lib.oracles import committee_assertions, direct_votes  # noqa: E402

PID, MODEL, ALPHA = ("HumanEval_0" if SUITE == "general" else None), "qwen3b", 0.1


def literal(key):
    """Display form of a canonical outcome key ('n' = number, 'f' = float, 's' = string)."""
    k = str(key)
    if PID == "HumanEval_0":   # has_close_elements returns a bool, which Python's equality treats as 0 or 1
        return {"('n', 0)": "False", "('n', 1)": "True"}.get(k, k)
    try:
        import ast
        t = ast.literal_eval(k)
        if isinstance(t, tuple) and t and t[0] in ("n", "f", "s"):
            return repr(t[1])
    except Exception:  # noqa: BLE001
        pass
    return k


def rows_for(ex, t_coral, t_conf):
    pos = {c: i for i, c in enumerate(ex["calls"])}
    res, ref = ex["results"], ex["results"]["ref"]
    mem = [f"{MODEL}_k{j}" for j in range(K_IMPL) if f"{MODEL}_k{j}" in res]
    dv = direct_votes(ex, [MODEL])
    spec_calls = {d["call"] for d in ex["doc"]}
    rows, seen = [], set()
    for a in ex.get("direct", {}).get(MODEL, {}).get("asserts", []):
        i = pos[a["call"]]
        if i in seen:
            continue
        seen.add(i)
        exp = ex["evals"].get(a["expected"])
        co = committee_assertions(ex, [i], mem, dv, w=W_DIRECT * K_IMPL, use_conf=True, n_channels=1)
        oracle, score = (co[0][1], co[0][2]) if co else (None, None)
        votes = [res[m][i] for m in mem]
        rows.append({"pid": ex["pid"], "model": MODEL, "call": a["call"], "from_spec_example": a["call"] in spec_calls, "direct_expected": exp,
                     "token_conf": a["conf_min"], "committee_agree_direct": sum(v == exp for v in votes), "committee_size": len(votes),
                     "committee_outcomes": " | ".join(votes), "coral_oracle": oracle, "coral_score": score,
                     "reference": ref[i], "direct_literal": literal(exp), "reference_literal": literal(ref[i]), "direct_correct": exp == ref[i],
                     "coral_correct": oracle == ref[i], "admitted_conf": (a["conf_min"] or 0) >= t_conf,
                     "admitted_coral": score is not None and score >= t_coral, "t_conf": t_conf, "t_coral": t_coral})
    return rows


def main():
    global PID
    crc = pd.read_csv(os.path.join(TABLES, "crc_splits_summary.csv"))
    thr = lambda meth: float(crc[(crc.bench == "All") & (crc.method == f"{meth}|{MODEL}") & (crc.alpha == ALPHA)].t_median.iloc[0])
    t_coral, t_conf = thr("CORAL"), thr("Direct+conf")
    EX = read_executions()
    if PID is None:
        for ex in EX:
            r = rows_for(ex, t_coral, t_conf)
            if any(not x["direct_correct"] and (x["token_conf"] or 0) >= 0.9 for x in r) and any(x["direct_correct"] for x in r):
                PID = ex["pid"]
                break
    ex = next(e for e in EX if e["pid"] == PID)
    T = pd.DataFrame(rows_for(ex, t_coral, t_conf))
    T.to_csv(os.path.join(TABLES, "worked_example.csv"), index=False)
    pd.set_option("display.width", 250)
    print(T.drop(columns=["pid", "model", "committee_outcomes"]).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
