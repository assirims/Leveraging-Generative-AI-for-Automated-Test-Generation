"""Step 6 - evaluate test oracles, false alarms, fault detection, coverage and risk control.

Methods (per test-writing model unless marked *):
  Doctest*            examples given in the specification (spec-provided oracles)
  Direct              assertions as written by the model (inputs and expected values predicted by the model)
  Direct+conf         the same assertions, admitted by the token probability of the expected value (calibrated by CRC)
  N-version vote      inputs of the model plus amplified inputs; expected value = majority output (>= 3 of 5) of the
                      model's spec-derived implementations
  CORAL               N-version committee plus the model's direct prediction, weighted by its token probability with weight
                      w = 2K (selected on the development model, dev_select_design.py); amplified inputs have no direct vote (the
                      channel abstains); score = weighted plurality share;
                      admission threshold calibrated by conformal risk control so that the probability of a false alarm on
                      a correct program is <= alpha
  CORAL-hetero*       CORAL with the pooled committee of both test-writing models
  Ideal oracle        inputs of the model with the reference output as expected value (upper bound for the inputs)
  Developer tests*    HumanEval `check` / QuixBugs test cases
Suites (CORAL_SUITE): general = HumanEval + QuixBugs (development); biomed = BioMedFn (biomedical evaluation, whose
seeded domain faults take the place of the real QuixBugs bugs). For the biomedical suite, the shift experiment
calibrates on all general problems and tests on the biomedical problems (transfer of a calibration).
Outputs: results/tables[/biomed]/*.csv and data/processed[/biomed]/*
"""
import json
import math
import os
import random
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats

from config import ALPHAS, GROUPS, K_IMPL, W_DIRECT, LLM_LABEL, N_BOOT, N_SPLITS, PROC_OUT, SEED, SUITE, TABLES, TEST_MODELS, read_executions
from lib.oracles import (NEG, committee_assertions, direct_assertions, direct_votes, doc_assertions, faulty_programs,
                         inputs_of, is_value, summarise)

INF = float("inf")


def load():
    return read_executions()


def members(ex, m, k=K_IMPL):
    return [f"{m}_k{j}" for j in range(k) if f"{m}_k{j}" in ex["results"]]


def models_in(EX):
    return [m for m in TEST_MODELS if any(m in ex["direct"] for ex in EX)]


def build(ex, models):
    """Scored assertion lists of every method for one problem."""
    S = {"Doctest": doc_assertions(ex)}
    allm = [m for m in models if m in ex["direct"]]
    for m in allm:
        X, XA = inputs_of(ex, [m], ("llm",)), inputs_of(ex, [m])
        mem = members(ex, m)
        dv = direct_votes(ex, [m])
        S[f"Direct|{m}"] = direct_assertions(ex, [m], "one")
        S[f"Direct+conf|{m}"] = direct_assertions(ex, [m], "conf")
        nv = committee_assertions(ex, XA, mem)
        S[f"N-version vote|{m}"] = [a for a in nv if a[3] >= math.ceil((K_IMPL + 1) / 2)]
        coral = lambda idx, mm, w: committee_assertions(ex, idx, mm, dv, w=w, use_conf=True, n_channels=1)
        S[f"CORAL|{m}"] = coral(XA, mem, W_DIRECT * K_IMPL)
        S[f"CORAL (committee only)|{m}"] = nv
        S[f"CORAL (no amplification)|{m}"] = coral(X, mem, W_DIRECT * K_IMPL)
        S[f"CORAL (w = K)|{m}"] = coral(XA, mem, float(K_IMPL))
        S[f"CORAL (unweighted direct vote)|{m}"] = committee_assertions(ex, XA, mem, dv)
        for k in range(1, K_IMPL + 1):
            S[f"CORAL K={k}|{m}"] = coral(XA, members(ex, m, k), W_DIRECT * k)
        ref = ex["results"]["ref"]
        S[f"Ideal oracle|{m}"] = [(i, ref[i], 1.0, 1, 1) for i in XA if is_value(ref[i])]
    if allm:
        XA = inputs_of(ex, allm)
        mem = [x for m in allm for x in members(ex, m)]
        S["CORAL-hetero"] = committee_assertions(ex, XA, mem, direct_votes(ex, allm), w=W_DIRECT * K_IMPL, use_conf=True, n_channels=len(allm))
    ref = ex["results"]["ref"]
    if ex["bench"] != "HumanEval":                  # input/output developer tests (QuixBugs, BioMedFn)
        H = [i for i, c in enumerate(ex["calls"]) if "human" in ex["sources"][c] and is_value(ref[i])]
        S["Developer tests"] = [(i, ref[i], 1.0, 1, 1) for i in H]
    return S


def problem_tables(EX, models):
    """Per problem: faulty programs, method summaries and coverage information."""
    P = []
    for ex in EX:
        faulty = faulty_programs(ex)
        S = build(ex, models)
        summ = {name: summarise(ex, a, faulty) for name, a in S.items()}
        if ex["bench"] == "HumanEval":   # developer tests = check(): detection from the check outcomes
            ch = ex["checks"]
            summ["Developer tests"] = {"w": NEG if ch.get("ref") == "PASS" else 1.0,
                                       "det": {b: (1.0 if ch.get(b) not in (None, "PASS") else NEG) for b in faulty},
                                       "n": None, "scores": [], "wrong_scores": [], "inputs": []}
        P.append({"pid": ex["pid"], "bench": ex["bench"], "group": ex.get("group", ex["bench"]), "faulty": faulty, "summ": summ, "cov": ex["coverage"],
                  "n_calls": len(ex["calls"])})
    return P


def hit(x, t):
    return x > NEG and x >= t


def suite_metrics(probs, method, t):
    """Metrics of the suites {score >= t} of `method` over a list of problems (t may be a dict pid -> threshold)."""
    fa, n_as, det = [], [], defaultdict(list)
    mut = []
    for p in probs:
        s = p["summ"].get(method)
        if s is None:
            continue
        tt = t[p["pid"]] if isinstance(t, dict) else t
        fa.append(1.0 if hit(s["w"], tt) else 0.0)
        n_as.append(sum(1 for x in s["scores"] if x >= tt) if s["n"] is not None else np.nan)
        kills = []
        for b, cls in p["faulty"].items():
            d = 1.0 if hit(s["det"].get(b, NEG), tt) else 0.0
            if cls == "mutant":
                kills.append(d)
            else:
                det[cls].append(d)
        if kills:
            mut.append(float(np.mean(kills)))
    return {"fa": float(np.mean(fa)) if fa else np.nan, "n_problems": len(fa), "asserts": float(np.nanmean(n_as)) if n_as else np.nan,
            "det_real": float(np.mean(det["real"])) if det["real"] else np.nan, "n_real": len(det["real"]),
            "det_llm": float(np.mean(det["llm"])) if det["llm"] else np.nan, "n_llm": len(det["llm"]),
            "mut_score": float(np.mean(mut)) if mut else np.nan, "n_mut_problems": len(mut)}


def crc_threshold(probs, method, alpha):
    """Smallest threshold t with (sum_p 1[w_p >= t] + 1) / (n + 1) <= alpha (conformal risk control, B = 1)."""
    ws = np.array([p["summ"][method]["w"] for p in probs if method in p["summ"]])
    grid = np.array(sorted({x for p in probs if method in p["summ"] for x in p["summ"][method]["scores"]} | {INF}))
    return crc_from_arrays(ws, grid, alpha)


def crc_from_arrays(ws, grid, alpha):
    """Vectorised CRC: at most k = floor((n + 1) alpha - 1) calibration problems may have w >= t."""
    n = len(ws)
    k = math.floor((n + 1) * alpha - 1 + 1e-12)
    if k < 0:
        return INF
    fin = np.sort(ws[ws > NEG])[::-1]
    if len(fin) <= k:
        return float(grid[0])
    j = np.searchsorted(grid, fin[k], side="right")      # smallest grid value strictly greater than the (k+1)-th largest w
    return float(grid[j]) if j < len(grid) else INF


class Arrays:
    """Per-method arrays for fast evaluation over many random splits."""
    def __init__(self, probs, method):
        self.idx = [i for i, p in enumerate(probs) if method in p["summ"]]
        S = [probs[i]["summ"][method] for i in self.idx]
        self.w = np.array([s["w"] for s in S])
        self.grid_sets = [set(s["scores"]) for s in S]
        self.nas = [np.array(s["scores"]) for s in S]
        self.det = {}
        for cls in ("real", "llm", "mutant"):
            pk, dv = [], []
            for j, i in enumerate(self.idx):
                for b, c in probs[i]["faulty"].items():
                    if c == cls:
                        pk.append(j)
                        dv.append(S[j]["det"].get(b, NEG))
            self.det[cls] = (np.array(pk, int), np.array(dv, float))

    def grid(self, mask):
        g = set()
        for j in np.flatnonzero(mask):
            g |= self.grid_sets[j]
        return np.array(sorted(g | {INF}))

    def metrics(self, mask, t):
        w = self.w[mask]
        fa = float(np.mean((w > NEG) & (w >= t))) if len(w) else np.nan
        out = {"fa": fa, "n_problems": int(mask.sum()),
               "asserts": float(np.mean([np.sum(self.nas[j] >= t) for j in np.flatnonzero(mask)])) if mask.any() else np.nan}
        for cls, key in (("real", "det_real"), ("llm", "det_llm")):
            pk, dv = self.det[cls]
            sel = mask[pk] if len(pk) else np.array([], bool)
            out[key] = float(np.mean((dv[sel] > NEG) & (dv[sel] >= t))) if sel.any() else np.nan
            out["n_" + cls] = int(sel.sum())
        pk, dv = self.det["mutant"]
        if len(pk):
            sel = mask[pk]
            hitv = ((dv > NEG) & (dv >= t)).astype(float)
            num = np.bincount(pk[sel], weights=hitv[sel], minlength=len(self.w))
            den = np.bincount(pk[sel], minlength=len(self.w))
            ok = den > 0
            out["mut_score"] = float(np.mean(num[ok] / den[ok])) if ok.any() else np.nan
        else:
            out["mut_score"] = np.nan
        return out


def coverage_at(p, method, t):
    s = p["summ"].get(method)
    cov = p["cov"]
    if s is None or cov is None:
        return np.nan, np.nan
    if method == "Developer tests" and p["bench"] == "HumanEval":
        c = cov["calls"][-1]
        L, B = set(c["l"]), set(c["b"])
    else:
        idx = {i for i, sc in s["inputs"] if sc >= t}
        L, B = set(), set()
        for i in idx:
            L |= set(cov["calls"][i]["l"])
            B |= set(cov["calls"][i]["b"])
    lc = len(L) / cov["n_lines"] if cov["n_lines"] else np.nan
    bc = len(B) / cov["n_branches"] if cov["n_branches"] else np.nan
    return lc, bc


def extra_tables(EX, P, models):
    """Assertion-level oracle data, threshold sweeps, committee correlation, model pass rates and costs."""
    rows = []
    for ex in EX:
        ref = ex["results"]["ref"]
        S = build(ex, models)
        X = {m: set(inputs_of(ex, [m], ("llm",))) for m in models}
        for name in [f"CORAL|{m}" for m in models] + [f"Direct+conf|{m}" for m in models] + ["CORAL-hetero"]:
            for (i, e, s, n, tot) in S.get(name, []):
                if ref[i] == "TIMEOUT":
                    continue
                m = name.split("|")[1] if "|" in name else "all"
                rows.append({"pid": ex["pid"], "bench": ex["bench"], "method": name.split("|")[0], "model": m, "score": s,
                             "votes": n, "voters": tot, "correct": int(ref[i] == e), "ref_valid": int(is_value(ref[i])),
                             "source": "llm" if (m != "all" and i in X[m]) else ("amp" if m != "all" else "pooled")})
    A = pd.DataFrame(rows)
    A.to_csv(os.path.join(PROC_OUT, "assertions.csv"), index=False)
    # reliability: accuracy by score bin
    rel = []
    for (meth, m), g in A.groupby(["method", "model"]):
        bins = np.linspace(0, 1, 11)
        g = g.assign(b=np.clip(np.digitize(g.score, bins[1:-1]), 0, 9))
        for b, h in g.groupby("b"):
            rel.append({"method": meth, "model": m, "bin": f"{bins[b]:.1f}-{bins[b + 1]:.1f}", "score_mean": h.score.mean(), "n": len(h),
                        "accuracy": h.correct.mean(), "llm_share": float((h.source == "llm").mean())})
    pd.DataFrame(rel).to_csv(os.path.join(TABLES, "oracle_reliability.csv"), index=False)
    # threshold sweep (all problems, no calibration): false-alarm rate vs detection
    sweep = []
    for meth in [f"{b}|{m}" for b in ("CORAL", "CORAL (committee only)", "Direct+conf", "CORAL (no amplification)") for m in models] + ["CORAL-hetero"]:
        grid = sorted({x for p in P if meth in p["summ"] for x in p["summ"][meth]["scores"]})
        if len(grid) > 60:
            grid = sorted(set(np.quantile(grid, np.linspace(0, 1, 60)).tolist()))
        for t in grid + [INF]:
            r = suite_metrics(P, meth, t)
            r.update({"method": meth, "t": t})
            sweep.append(r)
    pd.DataFrame(sweep).to_csv(os.path.join(TABLES, "threshold_sweep.csv"), index=False)
    # N-version committees: accuracy of the plurality and correlated failures (Knight & Leveson)
    corr = []
    for m in models + ["all"]:
        n_inp = n_maj = n_maj_wrong = n_unan = n_unan_wrong = n_any_right = 0
        for ex in EX:
            ref = ex["results"]["ref"]
            mem = [x for mm in (models if m == "all" else [m]) for x in members(ex, mm)]
            if not mem:
                continue
            for i in inputs_of(ex, models if m == "all" else [m]):
                if not is_value(ref[i]):
                    continue
                outs = [ex["results"][x][i] for x in mem]
                n_inp += 1
                from collections import Counter
                c = Counter(outs)
                win, v = c.most_common(1)[0]
                if v > len(mem) / 2:
                    n_maj += 1
                    n_maj_wrong += win != ref[i]
                if v == len(mem):
                    n_unan += 1
                    n_unan_wrong += win != ref[i]
                n_any_right += ref[i] in outs
        corr.append({"model": LLM_LABEL.get(m, f"Pooled ({K_IMPL * len(models)} versions)"), "inputs": n_inp, "majority_share": n_maj / max(n_inp, 1),
                     "majority_wrong": n_maj_wrong / max(n_maj, 1), "unanimous_share": n_unan / max(n_inp, 1),
                     "unanimous_wrong": n_unan_wrong / max(n_unan, 1), "some_version_right": n_any_right / max(n_inp, 1)})
    pd.DataFrame(corr).to_csv(os.path.join(TABLES, "committee_correlation.csv"), index=False)
    # model pass rates (developer tests) and generation cost
    mr = []
    for m in models + ["llama3b"]:
        greedy, samples, tok_t, sec_t, tok_i, sec_i, n_as, n_lines = [], [], [], [], [], [], [], []
        for ex in EX:
            for name, pr in ex["programs"].items():
                if pr.get("model") != m or pr["kind"] not in ("committee", "llm_impl"):
                    continue
                if ex["checks"]:
                    ok = ex["checks"].get(name) == "PASS"
                else:
                    ref = ex["results"]["ref"]
                    H = [i for i, c in enumerate(ex["calls"]) if "human" in ex["sources"][c]]
                    ok = all(ex["results"][name][i] == ref[i] for i in H)
                (greedy if pr["k"] == 0 else samples).append(ok)
                tok_i.append(pr["tokens"])
                sec_i.append(pr["seconds"])
            d = ex["direct"].get(m)
            if d:
                tok_t.append(d["tokens"])
                sec_t.append(d["seconds"])
                n_as.append(len(d["asserts"]))
                n_lines.append(d["n_lines"])
        acc = []
        for ex in EX:
            ref = ex["results"]["ref"]
            pos = {c: i for i, c in enumerate(ex["calls"])}
            for a in ex["direct"].get(m, {}).get("asserts", []):
                e = ex["evals"].get(a["expected"])
                if ref[pos[a["call"]]] == "TIMEOUT":
                    continue
                acc.append(int(e is not None and ref[pos[a["call"]]] == e))
        mr.append({"model": LLM_LABEL[m], "pass_greedy": float(np.mean(greedy)) if greedy else np.nan, "pass_sampled": float(np.mean(samples)) if samples else np.nan,
                   "n_problems": len(greedy), "test_tokens": float(np.mean(tok_t)) if tok_t else np.nan, "test_seconds": float(np.mean(sec_t)) if sec_t else np.nan,
                   "impl_tokens": float(np.mean(tok_i)) if tok_i else np.nan, "impl_seconds": float(np.mean(sec_i)) if sec_i else np.nan,
                   "asserts_parsed": float(np.mean(n_as)) if n_as else np.nan, "assert_lines": float(np.mean(n_lines)) if n_lines else np.nan,
                   "direct_oracle_accuracy": float(np.mean(acc)) if acc else np.nan, "n_direct_asserts": len(acc)})
    pd.DataFrame(mr).to_csv(os.path.join(TABLES, "models_overview.csv"), index=False)


def bootstrap_main(P, xfit, models, n_boot=N_BOOT):
    """Bootstrap (over problems) 95% intervals of the main measures for the main methods (all problems)."""
    rng = np.random.default_rng(SEED)
    rows = []
    specs = [("Developer tests", None), ("Doctest", None)]
    for m in models:
        specs += [(f"Direct|{m}", None), (f"Direct+conf|{m}", 0.1), (f"CORAL|{m}", 0.1), (f"N-version vote|{m}", None)]
    specs += [("CORAL-hetero", 0.1)]
    for meth, a in specs:
        th = -INF if a is None else xfit.get((meth, a))
        if th is None:
            continue
        probs = [p for p in P if meth in p["summ"]]
        if not probs:
            continue
        # per-problem contributions
        fa = np.array([1.0 if hit(p["summ"][meth]["w"], th if not isinstance(th, dict) else th[p["pid"]]) else 0.0 for p in probs])
        def det_of(cls):
            out = []
            for k, p in enumerate(probs):
                t = th if not isinstance(th, dict) else th[p["pid"]]
                for b, c in p["faulty"].items():
                    if c == cls:
                        out.append((k, 1.0 if hit(p["summ"][meth]["det"].get(b, NEG), t) else 0.0))
            return out
        dr, dl = det_of("real"), det_of("llm")
        ms = []
        for k, p in enumerate(probs):
            t = th if not isinstance(th, dict) else th[p["pid"]]
            ks = [1.0 if hit(p["summ"][meth]["det"].get(b, NEG), t) else 0.0 for b, c in p["faulty"].items() if c == "mutant"]
            if ks:
                ms.append((k, float(np.mean(ks))))
        n = len(probs)
        B = {"fa": [], "det_real": [], "det_llm": [], "mut_score": []}
        dr_k = np.array([k for k, _ in dr]); dr_v = np.array([v for _, v in dr])
        dl_k = np.array([k for k, _ in dl]); dl_v = np.array([v for _, v in dl])
        ms_k = np.array([k for k, _ in ms]); ms_v = np.array([v for _, v in ms])
        for _ in range(n_boot):
            w = np.bincount(rng.integers(0, n, n), minlength=n).astype(float)
            B["fa"].append(np.average(fa, weights=w) if w.sum() else np.nan)
            for key, kk, vv in (("det_real", dr_k, dr_v), ("det_llm", dl_k, dl_v), ("mut_score", ms_k, ms_v)):
                ww = w[kk] if len(kk) else np.array([])
                B[key].append(np.average(vv, weights=ww) if len(kk) and ww.sum() > 0 else np.nan)
        r = {"method": meth, "alpha": a}
        for key, vals in B.items():
            vals = np.array(vals, float)
            r[key + "_lo"], r[key + "_hi"] = (float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))) if np.isfinite(vals).any() else (np.nan, np.nan)
        rows.append(r)
    pd.DataFrame(rows).to_csv(os.path.join(TABLES, "bootstrap_ci.csv"), index=False)


def main():
    EX = load()
    models = models_in(EX)
    P = problem_tables(EX, models)
    rng = random.Random(SEED)
    methods = sorted({k for p in P for k in p["summ"]})
    uncond = [m for m in methods if m.split("|")[0] in ("Doctest", "Direct", "N-version vote", "Ideal oracle", "Developer tests")]
    calibrated = [m for m in methods if m not in uncond]
    rows = []
    # ---------------------------------------------------------------- unconditional methods, all problems
    for bench in GROUPS + ["All"]:
        probs = [p for p in P if bench == "All" or p["group"] == bench]
        for m in uncond:
            r = suite_metrics(probs, m, -INF)
            lc = [coverage_at(p, m, -INF) for p in probs if m in p["summ"]]
            r.update({"bench": bench, "method": m, "alpha": None, "line_cov": float(np.nanmean([x[0] for x in lc])) if lc else np.nan,
                      "branch_cov": float(np.nanmean([x[1] for x in lc])) if lc else np.nan})
            rows.append(r)
    # ---------------------------------------------------------------- calibrated methods: random splits (validity)
    split_rows = []
    for bench in (("HumanEval", "All") if SUITE == "general" else ("All",)):
        probs = [p for p in P if bench == "All" or p["bench"] == bench]
        AR = {m: Arrays(probs, m) for m in calibrated}
        for s in range(N_SPLITS):
            idx = list(range(len(probs)))
            rng.shuffle(idx)
            half = len(idx) // 2
            cal_set = set(idx[:half])
            for m in calibrated:
                ar = AR[m]
                cal_mask = np.array([i in cal_set for i in ar.idx])
                test_mask = ~cal_mask
                grid = ar.grid(cal_mask)
                for a in ALPHAS:
                    t = crc_from_arrays(ar.w[cal_mask], grid, a)
                    r = ar.metrics(test_mask, t)
                    r.update({"bench": bench, "method": m, "alpha": a, "split": s, "t": t})
                    split_rows.append(r)
    SR = pd.DataFrame(split_rows)
    agg = SR.groupby(["bench", "method", "alpha"]).agg(
        fa_mean=("fa", "mean"), fa_sd=("fa", "std"), share_ok=("fa", lambda x: None), det_real=("det_real", "mean"),
        det_llm=("det_llm", "mean"), mut_score=("mut_score", "mean"), asserts=("asserts", "mean"), t_median=("t", "median")).reset_index()
    for i, r in agg.iterrows():
        x = SR[(SR.bench == r.bench) & (SR.method == r.method) & (SR.alpha == r.alpha)]
        agg.loc[i, "share_ok"] = float(np.mean(x.fa <= r.alpha))
    agg["n_splits"] = N_SPLITS
    agg.to_csv(os.path.join(TABLES, "crc_splits_summary.csv"), index=False)
    SR.to_csv(os.path.join(PROC_OUT, "crc_splits.csv"), index=False)
    # ---------------------------------------------------------------- shift: calibrate on one population, test on another
    #   general suite: calibrate on HumanEval, test on QuixBugs
    #   biomed suite:  calibrate on all general problems (HumanEval + QuixBugs), test on the biomedical problems
    if SUITE == "general":
        he, qb = [p for p in P if p["bench"] == "HumanEval"], [p for p in P if p["bench"] == "QuixBugs"]
        shift_file = "crc_shift_quixbugs.csv"
    else:
        EXg = read_executions("general")
        he, qb = problem_tables(EXg, models_in(EXg)), P
        shift_file = "crc_transfer_general.csv"
    shift = []
    for m in calibrated:
        for a in ALPHAS:
            t = crc_threshold(he, m, a)
            r = suite_metrics(qb, m, t)
            r.update({"method": m, "alpha": a, "t": t})
            shift.append(r)
    pd.DataFrame(shift).to_csv(os.path.join(TABLES, shift_file), index=False)
    # ---------------------------------------------------------------- cross-fitting (2 folds) for per-problem decisions
    order = list(range(len(P)))
    random.Random(SEED + 1).shuffle(order)
    folds = [set(order[: len(P) // 2]), set(order[len(P) // 2:])]
    xfit = {}
    for m in calibrated:
        for a in ALPHAS:
            th = {}
            for f in (0, 1):
                cal = [P[i] for i in folds[1 - f]]
                t = crc_threshold(cal, m, a)
                for i in folds[f]:
                    th[P[i]["pid"]] = t
            xfit[(m, a)] = th
    json.dump({f"{m}@{a}": th for (m, a), th in xfit.items()}, open(os.path.join(PROC_OUT, "xfit_thresholds.json"), "w"))
    for bench in GROUPS + ["All"]:
        probs = [p for p in P if bench == "All" or p["group"] == bench]
        for (m, a), th in xfit.items():
            r = suite_metrics(probs, m, th)
            lc = [coverage_at(p, m, th[p["pid"]]) for p in probs if m in p["summ"]]
            r.update({"bench": bench, "method": m, "alpha": a, "line_cov": float(np.nanmean([x[0] for x in lc])),
                      "branch_cov": float(np.nanmean([x[1] for x in lc]))})
            rows.append(r)
    T = pd.DataFrame(rows)
    T["model"] = T.method.map(lambda s: LLM_LABEL.get(s.split("|")[1], "") if "|" in s else "")
    T["method_name"] = T.method.map(lambda s: s.split("|")[0])
    T.to_csv(os.path.join(TABLES, "methods_summary.csv"), index=False)
    # ---------------------------------------------------------------- paired comparisons on cross-fitted decisions
    paired = []

    def thr(meth, a):
        if meth.split("|")[0] in ("Direct", "N-version vote", "Doctest", "Developer tests", "Ideal oracle"):
            return None
        return xfit.get((meth, a))

    def compare(A, B, a, label):
        thA, thB = thr(A, a), thr(B, a)
        if (thA is None and A.split("|")[0] not in ("Direct", "N-version vote")) or (thB is None and B.split("|")[0] not in ("Direct", "N-version vote")):
            return
        fa_x, fa_y, det_x, det_y, mu_x, mu_y = [], [], [], [], [], []
        for p in P:
            sa, sb = p["summ"].get(A), p["summ"].get(B)
            if sa is None or sb is None:
                continue
            ta = -INF if thA is None else thA[p["pid"]]
            tb = -INF if thB is None else thB[p["pid"]]
            fa_x.append(hit(sa["w"], ta))
            fa_y.append(hit(sb["w"], tb))
            ka, kb = [], []
            for b, cls in p["faulty"].items():
                da, db = hit(sa["det"].get(b, NEG), ta), hit(sb["det"].get(b, NEG), tb)
                if cls in ("real", "llm"):
                    det_x.append(da)
                    det_y.append(db)
                else:
                    ka.append(da)
                    kb.append(db)
            if ka:
                mu_x.append(np.mean(ka))
                mu_y.append(np.mean(kb))
        for what, x, y in (("false_alarm", fa_x, fa_y), ("detection_real_llm", det_x, det_y)):
            x, y = np.array(x, bool), np.array(y, bool)
            b01, b10 = int(np.sum(~x & y)), int(np.sum(x & ~y))
            p_mc = stats.binomtest(min(b01, b10), b01 + b10, 0.5).pvalue if b01 + b10 > 0 else 1.0
            paired.append({"comparison": label, "alpha": a, "measure": what, "rate_A": float(x.mean()) if len(x) else np.nan,
                           "rate_B": float(y.mean()) if len(y) else np.nan, "n": len(x), "only_B": b01, "only_A": b10, "p": p_mc, "test": "McNemar (exact)"})
        x, y = np.array(mu_x), np.array(mu_y)
        nz = np.sum(x != y)
        p_w = stats.wilcoxon(x, y).pvalue if nz > 0 else 1.0
        paired.append({"comparison": label, "alpha": a, "measure": "mutation_score", "rate_A": float(x.mean()) if len(x) else np.nan,
                       "rate_B": float(y.mean()) if len(y) else np.nan, "n": len(x), "only_B": int(np.sum(y > x)), "only_A": int(np.sum(x > y)), "p": p_w, "test": "Wilcoxon signed-rank"})

    for m in models:
        for a in ALPHAS:
            compare(f"Direct+conf|{m}", f"CORAL|{m}", a, f"{LLM_LABEL[m]}: Direct + confidence (A) vs CORAL (B)")
            compare(f"Direct|{m}", f"CORAL|{m}", a, f"{LLM_LABEL[m]}: Direct (A) vs CORAL (B)")
            compare(f"CORAL (committee only)|{m}", f"CORAL|{m}", a, f"{LLM_LABEL[m]}: committee only (A) vs CORAL (B)")
            compare(f"CORAL (no amplification)|{m}", f"CORAL|{m}", a, f"{LLM_LABEL[m]}: no amplification (A) vs CORAL (B)")
    if models:
        big = models[-1]
        for a in ALPHAS:
            compare(f"CORAL|{big}", "CORAL-hetero", a, f"CORAL {LLM_LABEL[big]} (A) vs pooled committee (B)")
    pd.DataFrame(paired).to_csv(os.path.join(TABLES, "paired_tests.csv"), index=False)
    json.dump({"models": models, "n_problems": len(P), "faults": {
        "real": sum(v == "real" for p in P for v in p["faulty"].values()),
        "llm": sum(v == "llm" for p in P for v in p["faulty"].values()),
        "mutant": sum(v == "mutant" for p in P for v in p["faulty"].values())}},
        open(os.path.join(PROC_OUT, "analysis_meta.json"), "w"), indent=1)
    extra_tables(EX, P, models)
    bootstrap_main(P, xfit, models)
    print("problems", len(P), "models", models)
    show = T[(T.bench == "All") & (T.alpha.isna() | (T.alpha == 0.1))][["method", "alpha", "fa", "asserts", "det_real", "det_llm", "mut_score", "line_cov", "branch_cov"]]
    print(show.round(3).to_string())
    print(agg[(agg.bench == "All") & (agg.alpha == 0.1)][["method", "fa_mean", "share_ok", "det_real", "det_llm", "mut_score", "asserts"]].round(3).to_string())


if __name__ == "__main__":
    main()
