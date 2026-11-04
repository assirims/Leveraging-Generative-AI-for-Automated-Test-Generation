"""Step 8 - collect every number quoted in the manuscript into results/paper_numbers[_biomed].json (per suite)."""
import json
import os

import numpy as np
import pandas as pd

from config import ALPHAS, DEV_SPLITS, K_IMPL, N_BOOT, LLM_LABEL, MAX_MUTANTS, N_AMPLIFY, N_ASSERT, N_SPLITS, PROBLEMS_FILE, PROC_OUT, RESULTS, SUFFIX, SUITE, TABLES, TEST_MODELS, read_executions
from lib.oracles import faulty_programs, is_value


def records(df):
    return json.loads(df.replace({np.nan: None}).to_json(orient="records"))


def main():
    EX = read_executions()
    n_mut = n_kill = n_real = n_llm = n_llm_impl = 0
    n_inputs, n_llm_in, n_amp_in, ref_to, ref_exc, n_calls = [], [], [], 0, 0, 0
    per_bench = {}
    for ex in EX:
        f = faulty_programs(ex)
        b = per_bench.setdefault(ex.get("group", ex["bench"]), {"problems": 0, "mutants": 0, "killable": 0, "real": 0, "llm": 0, "llm_impl": 0, "doc": 0})
        b["problems"] += 1
        b["doc"] += int(bool(ex["doc"]))
        for name, pr in ex["programs"].items():
            if pr["kind"] == "mutant":
                n_mut += 1
                b["mutants"] += 1
            if pr["kind"] == "llm_impl":
                n_llm_impl += 1
                b["llm_impl"] += 1
        for name, cls in f.items():
            if cls == "mutant":
                n_kill += 1
                b["killable"] += 1
            elif cls == "real":
                n_real += 1
                b["real"] += 1
            else:
                n_llm += 1
                b["llm"] += 1
        ref = ex["results"]["ref"]
        n_calls += len(ref)
        ref_to += sum(k == "TIMEOUT" for k in ref)
        ref_exc += sum(not is_value(k) and k != "TIMEOUT" for k in ref)
        for m in TEST_MODELS:
            if m in ex["direct"]:
                n_llm_in.append(len(ex["direct"][m]["asserts"]))
                n_amp_in.append(len(ex["direct"][m]["amplified"]))
        n_inputs.append(len(ex["calls"]))
    meta = json.load(open(os.path.join(PROC_OUT, "analysis_meta.json")))
    N = {
        "data": {"n_problems": len(EX), "per_bench": per_bench, "mutants": n_mut, "killable_mutants": n_kill, "real_faults": n_real,
                 "llm_faults": n_llm, "llm_impls": n_llm_impl, "mean_inputs_per_problem": float(np.mean(n_inputs)),
                 "mean_llm_asserts": float(np.mean(n_llm_in)) if n_llm_in else None, "mean_amplified": float(np.mean(n_amp_in)) if n_amp_in else None,
                 "calls": n_calls, "ref_timeouts": ref_to, "ref_exceptions": ref_exc},
        "settings": {"K": K_IMPL, "n_assert": N_ASSERT, "n_amplify": N_AMPLIFY, "max_mutants": MAX_MUTANTS, "splits": N_SPLITS, "alphas": list(ALPHAS), "n_boot": N_BOOT, "dev_splits": DEV_SPLITS},
        "models": meta["models"], "labels": LLM_LABEL,
        "models_overview": records(pd.read_csv(os.path.join(TABLES, "models_overview.csv"))),
        "methods": records(pd.read_csv(os.path.join(TABLES, "methods_summary.csv"))),
        "crc": records(pd.read_csv(os.path.join(TABLES, "crc_splits_summary.csv"))),
        "shift": records(pd.read_csv(os.path.join(TABLES, "crc_shift_quixbugs.csv" if SUITE == "general" else "crc_transfer_general.csv"))),
        "paired": records(pd.read_csv(os.path.join(TABLES, "paired_tests.csv"))),
        "reliability": records(pd.read_csv(os.path.join(TABLES, "oracle_reliability.csv"))),
        "committee": records(pd.read_csv(os.path.join(TABLES, "committee_correlation.csv"))),
        "bootstrap": records(pd.read_csv(os.path.join(TABLES, "bootstrap_ci.csv"))),
        "high_probability": records(pd.read_csv(os.path.join(TABLES, "high_probability.csv"))) if os.path.exists(os.path.join(TABLES, "high_probability.csv")) else [],
        "worked_example": records(pd.read_csv(os.path.join(TABLES, "worked_example.csv"), dtype={"direct_literal": str, "reference_literal": str})) if os.path.exists(os.path.join(TABLES, "worked_example.csv")) else [],
        "dev_design": records(pd.read_csv(os.path.join(TABLES, "dev_design_selection.csv"))) if os.path.exists(os.path.join(TABLES, "dev_design_selection.csv")) else [],
    }
    # committee-only and unweighted variants at their strictest non-empty threshold (unanimity), from the threshold sweep
    W = pd.read_csv(os.path.join(TABLES, "threshold_sweep.csv"))
    N["strictest"] = []
    for meth in sorted(set(W.method)):
        g = W[(W.method == meth) & (W.asserts > 0)].sort_values("t", ascending=False)
        if len(g):
            r = g.iloc[0]
            N["strictest"].append({"method": meth, "t": float(r.t), "fa": float(r.fa), "asserts": float(r.asserts), "mut_score": float(r.mut_score)})
    N["suite"] = SUITE
    fcd = os.path.join(TABLES, "fault_category_detection.csv")
    if os.path.exists(fcd):
        N["fault_detection"] = records(pd.read_csv(fcd))
    if SUITE == "biomed":       # benchmark description (domains, seeded fault classes) from the built problems
        probs = [json.loads(l) for l in open(PROBLEMS_FILE)]
        N["benchmark"] = [{k: p[k] for k in ("pid", "entry", "domain", "topic", "source", "fault_class", "fault_category")} | {"developer_tests": len(p["human_io"])}
                          for p in probs]
    out = os.path.join(RESULTS, f"paper_numbers{SUFFIX}.json")
    json.dump(N, open(out, "w"), indent=1)
    print("wrote", os.path.relpath(out, RESULTS), {k: v for k, v in N["data"].items() if k != "per_bench"})


if __name__ == "__main__":
    main()
