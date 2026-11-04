"""Oracle construction (direct LLM predictions, N-version committees, CORAL) and suite-level outcome summaries.

An assertion is (input index, expected outcome key, score). A suite at threshold t keeps the assertions with
score >= t. Because suites are nested in t, every quantity we need is a step function of t and is summarised by a
single number per problem or program:
  w   = max score among WRONG assertions (the suite raises a false alarm on the correct program iff t <= w)
  d_b = max score among CORRECT assertions that fail on faulty program b (b is detected iff t <= d_b)
"""
from collections import Counter

NEG = float("-inf")


def is_value(k):
    return not (k.startswith("EXC:") or k == "TIMEOUT" or k.startswith("LOAD:"))


def plurality(outcomes, prefer=None):
    """Most frequent outcome (ties: the `prefer` outcome if tied, else lexicographic) and its vote count."""
    c = Counter(outcomes)
    if not c:
        return None, 0
    top = max(c.values())
    tied = sorted(k for k, v in c.items() if v == top)
    win = prefer if prefer in tied else tied[0]
    return win, top


def committee_assertions(ex, idx, members, direct_votes=None, w=1.0, use_conf=False, allowed=None, n_channels=None):
    """Assertions with N-version (committee) oracles.

    ex: execution record; idx: input indices; members: committee program names; direct_votes: dict input index ->
    list of (expected key, token confidence) predicted directly by models; each direct prediction adds a vote of
    weight w (times its token confidence if use_conf). Score = weighted plurality votes / total weight; no assertion
    if the plurality outcome is an error or a timeout. allowed: optional set of admissible input indices.
    n_channels: if given, the total weight always includes w for each of n_channels direct-prediction channels, so that
    an input without a direct prediction (an amplified input) is scored as if that channel had abstained."""
    res = ex["results"]
    out = []
    for i in idx:
        if allowed is not None and i not in allowed:
            continue
        V = Counter(res[m][i] for m in members)
        tot = float(len(members)) + (w * n_channels if n_channels is not None else 0.0)
        for e, c in (direct_votes or {}).get(i, []):
            V[e] += w * (c if use_conf else 1.0)
            if n_channels is None:
                tot += w
        if not V or tot == 0:
            continue
        prefer = res[members[0]][i] if members else None
        top = max(V.values())
        tied = sorted(k for k, v in V.items() if abs(v - top) < 1e-12)
        win = prefer if prefer in tied else tied[0]
        if not is_value(win):
            continue
        out.append((i, win, top / tot, top, tot))
    return out


def informative_inputs(ex, m, idx):
    """Inputs that distinguish at least one mutant of model m's own greedy implementation from that implementation
    (mutation-based input selection that uses neither the reference nor the program under test)."""
    res = ex["results"]
    base = res.get(f"{m}_k0")
    selfm = [n for n in res if n.startswith(f"self:{m}:")]
    if base is None or not selfm:
        return set(idx)
    return {i for i in idx if any(res[s][i] != base[i] for s in selfm)}


def direct_assertions(ex, models, score="one"):
    """Assertions written by the models: expected value as predicted; score 1 or the token confidence."""
    pos = {c: i for i, c in enumerate(ex["calls"])}
    out = []
    for m in models:
        for a in ex["direct"].get(m, {}).get("asserts", []):
            e = ex["evals"].get(a["expected"])
            if e is None or not is_value(e):
                continue
            s = 1.0 if score == "one" else (a["conf_min"] if a["conf_min"] is not None else 0.0)
            out.append((pos[a["call"]], e, s, 1, 1))
    return out


def direct_votes(ex, models):
    """input index -> list of (expected key, token confidence), one per model (its first assertion on that input)."""
    pos = {c: i for i, c in enumerate(ex["calls"])}
    dv = {}
    for m in models:
        seen = set()
        for a in ex["direct"].get(m, {}).get("asserts", []):
            e = ex["evals"].get(a["expected"])
            i = pos[a["call"]]
            if e is not None and is_value(e) and i not in seen:
                seen.add(i)
                dv.setdefault(i, []).append((e, a["conf_min"] if a["conf_min"] is not None else 0.0))
    return dv


def doc_assertions(ex):
    pos = {c: i for i, c in enumerate(ex["calls"])}
    out = []
    for d in ex["doc"]:
        e = ex["evals"].get(d["expected"])
        if e is not None and is_value(e):
            out.append((pos[d["call"]], e, 1.0, 1, 1))
    return out


def inputs_of(ex, models, kinds=("llm", "amp")):
    want = {f"{k}:{m}" for k in kinds for m in models}
    return [i for i, c in enumerate(ex["calls"]) if want & set(ex["sources"][c])]


def faulty_programs(ex):
    """Faulty programs of a problem with their fault class.

    real_bug: QuixBugs original program; llm_fault: Llama-3.2-3B implementation that fails the developer tests or
    differs from the reference on a valid input; mutant: first-order mutant that differs from the reference on a
    valid input of the pooled input set or fails the developer tests (non-killable mutants are treated as equivalent)."""
    res, ref = ex["results"], ex["results"]["ref"]
    valid = [i for i, k in enumerate(ref) if is_value(k)]
    out = {}
    for name, pr in ex["programs"].items():
        if pr["kind"] not in ("real_bug", "llm_impl", "mutant"):
            continue
        differs = any(res[name][i] != ref[i] for i in valid)
        fails_dev = ex["checks"].get(name) not in (None, "PASS") if ex["checks"] else False
        if differs or fails_dev:
            out[name] = {"real_bug": "real", "llm_impl": "llm", "mutant": "mutant"}[pr["kind"]]
    return out


def summarise(ex, asserts, faulty):
    """Per-problem step-function summary of a scored assertion list."""
    res, ref = ex["results"], ex["results"]["ref"]
    w = NEG
    correct = []
    # inputs on which the reference program does not terminate within the time limit have no known expected outcome
    asserts = [a for a in asserts if ref[a[0]] != "TIMEOUT"]
    for (i, e, s, *_rest) in asserts:
        if ref[i] != e:
            w = max(w, s)
        else:
            correct.append((i, e, s))
    det = {}
    for b in faulty:
        rb = res[b]
        det[b] = max((s for (i, e, s) in correct if rb[i] != e), default=NEG)
    return {"w": w, "det": det, "n": len(asserts), "scores": sorted((a[2] for a in asserts), reverse=True),
            "wrong_scores": sorted((a[2] for a in asserts if ref[a[0]] != a[1]), reverse=True),
            "inputs": [(a[0], a[2]) for a in asserts]}
