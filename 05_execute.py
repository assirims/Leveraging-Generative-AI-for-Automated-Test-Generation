"""Step 5 - execute everything that the analysis needs, once, in the sandbox.

Per problem:
  inputs     call expressions from (i) each model's assertions, (ii) type-aware amplification of each model's inputs,
             (iii) doctest examples of the specification and (iv) the developer test cases (QuixBugs);
  programs   reference (correct) implementation, real buggy version (QuixBugs), Llama-3.2-3B implementation
             (LLM-made faults), first-order mutants of the reference, and the K spec-derived implementations of each model;
  outputs    canonical outcome of every program on every input, expected values of all assertions, HumanEval developer
             tests (`check`) on every program, and line/branch coverage of the reference per input.
Results are cached per problem (data/processed/exec/<pid>.json), so the step can be re-run as more model outputs arrive.
Usage: python 05_execute.py [n_workers]   (suite from CORAL_SUITE: general | biomed)
"""
import concurrent.futures as cf
import hashlib
import json
import os
import sys
import time
import zlib

from config import CALL_TIMEOUT, K_IMPL, MAX_MUTANTS, N_AMPLIFY, N_SELFMUT, PROBLEMS_FILE, PROC, SEED, SUFFIX, SUITE, TEST_MODELS, llm_log
from lib import execution as ex
from lib.assertions import assemble, parse_assertion, parse_tests
from lib.mutation import mutants

EXEC = os.path.join(PROC, "exec")
os.makedirs(EXEC, exist_ok=True)
H = lambda s: hashlib.sha1(s.encode()).hexdigest()[:16]


def load_generations():
    gens = {}
    for m in TEST_MODELS + ["llama3b"]:
        f = llm_log(m)
        if not os.path.exists(f):
            continue
        for line in open(f, encoding="utf-8"):
            d = json.loads(line)
            kind, pid = d["tag"].split(":")[:2]
            g = gens.setdefault(pid, {}).setdefault(m, {"tests": None, "impls": {}})
            if kind == "test":
                g["tests"] = d
            else:
                g["impls"][int(d["tag"].split(":")[2])] = d
    return gens


def process(p, gen, n_workers):
    pid, entry = p["pid"], p["entry"]
    cache_f = os.path.join(EXEC, pid + ".json")
    cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {"runs": {}, "checks": {}, "evals": {}, "amp": {}}
    calls, sources = [], {}

    def add(c, src):
        if c not in sources:
            sources[c] = []
            calls.append(c)
        if src not in sources[c]:
            sources[c].append(src)

    # ---- model assertions (direct oracles) and their inputs
    direct = {}
    for m in TEST_MODELS:
        t = (gen.get(m) or {}).get("tests")
        if t is None:
            continue
        asserts, n_lines = parse_tests(t["text"], entry, t.get("probs"))
        asserts = [a for a in asserts if a["wrap"] in (None, "list")]
        direct[m] = {"asserts": asserts, "n_lines": n_lines, "tokens": t["tokens"], "seconds": t["seconds"]}
        for a in asserts:
            add(a["call"], "llm:" + m)
    # ---- amplified inputs (no model call)
    for m in direct:
        base = [a["call"] for a in direct[m]["asserts"]]
        k = f"{m}:{H(json.dumps(base))}"
        if k not in cache["amp"]:
            cache["amp"][k] = ex.amplify(entry, base, N_AMPLIFY, zlib.crc32(f"{SEED}:{pid}:{m}".encode()))
        direct[m]["amplified"] = cache["amp"][k]
        for c in cache["amp"][k]:
            add(c, "amp:" + m)
    # ---- doctest examples and developer test inputs
    doc = []
    for call, exp in p["doc_examples"]:
        r = parse_assertion(f"assert {call} == {exp}", entry)
        if r and r[2] in (None, "list"):
            doc.append({"call": r[0], "expected": r[1]})
            add(r[0], "doc")
    if p["human_io"]:
        for args, _ in p["human_io"]:
            add(f"{entry}(*{args!r})", "human")
    # ---- expected values of all assertions
    exprs = sorted({a["expected"] for m in direct for a in direct[m]["asserts"]} | {d["expected"] for d in doc})
    todo = [e for e in exprs if e not in cache["evals"]]
    for e, kk in zip(todo, ex.eval_exprs(todo)):
        cache["evals"][e] = kk
    # ---- programs
    progs = {"ref": {"src": p["ref_src"], "kind": "ref"}}
    if p["buggy_src"]:
        progs["bug"] = {"src": p["buggy_src"], "kind": "real_bug"}
    for i, (op, src) in enumerate(mutants(p["ref_src"], entry, MAX_MUTANTS, SEED)):
        progs[f"mut{i}"] = {"src": src, "kind": "mutant", "op": op}
    for m in TEST_MODELS + ["llama3b"]:
        for k, d in sorted(((gen.get(m) or {}).get("impls") or {}).items()):
            src, ok = assemble(p["spec"], d["text"])
            name = "llama" if m == "llama3b" else f"{m}_k{k}"
            progs[name] = {"src": src, "kind": "llm_impl" if m == "llama3b" else "committee", "model": m, "k": k,
                           "compiles": ok, "tokens": d["tokens"], "seconds": d["seconds"]}
    # ---- self-mutants of each model's greedy implementation (used only to judge how informative an input is;
    #      they are derived from the committee, never from the reference or the program under test)
    for m in (TEST_MODELS[:1] if SUITE == "general" else []):   # development model, general suite only (design selection)
        g = progs.get(f"{m}_k0")
        if g and g["compiles"]:
            try:
                sm = mutants(g["src"], entry, N_SELFMUT, SEED)
            except Exception:
                sm = []
            for i, (op, src) in enumerate(sm):
                progs[f"self:{m}:{i}"] = {"src": src, "kind": "selfmut", "model": m, "op": op}
    # ---- run
    jobs = []
    for name, pr in progs.items():
        h = H(pr["src"])
        pr["hash"] = h
        done = cache["runs"].setdefault(h, {})
        missing = [c for c in calls if c not in done]
        if missing:
            jobs.append((h, pr["src"], missing))
    with cf.ThreadPoolExecutor(n_workers) as pool:
        futs = {pool.submit(ex.run_program, src, miss, CALL_TIMEOUT, 30.0): (h, miss) for h, src, miss in jobs}
        for f in cf.as_completed(futs):
            h, miss = futs[f]
            for c, kk in zip(miss, f.result()):
                cache["runs"][h][c] = kk
        if p["human_check"]:
            cj = [(pr["hash"], pr["src"]) for pr in progs.values() if pr["hash"] not in cache["checks"] and pr["kind"] != "selfmut"]
            futs = {pool.submit(ex.check, src, p["human_check"], entry): h for h, src in cj}
            for f in cf.as_completed(futs):
                cache["checks"][futs[f]] = f.result()
    # ---- coverage of the reference per input (and of the developer tests)
    cov_key = H(json.dumps(calls))
    if cache.get("cov_key") != cov_key:
        cache["coverage"] = ex.coverage(p["ref_src"], calls, p["human_check"], entry)
        cache["cov_key"] = cov_key
    json.dump(cache, open(cache_f, "w"))
    out = {"pid": pid, "bench": p["bench"], "group": p.get("domain", p["bench"]), "entry": entry, "calls": calls, "sources": sources, "direct": direct, "doc": doc,
           "evals": {e: cache["evals"][e] for e in exprs},
           "programs": {n: {k: v for k, v in pr.items() if k != "src"} for n, pr in progs.items()},
           "results": {n: [cache["runs"][pr["hash"]][c] for c in calls] for n, pr in progs.items()},
           "checks": {n: cache["checks"].get(pr["hash"]) for n, pr in progs.items()} if p["human_check"] else {},
           "coverage": cache["coverage"]}
    return out


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    probs = [json.loads(l) for l in open(PROBLEMS_FILE)]
    gens = load_generations()
    t0 = time.time()
    with open(os.path.join(PROC, f"executions{SUFFIX}.jsonl"), "w") as fh:
        for i, p in enumerate(probs):
            if only and p["pid"] not in only:
                continue
            out = process(p, gens.get(p["pid"], {}), n_workers)
            fh.write(json.dumps(out) + "\n")
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(probs)}  {time.time() - t0:.0f}s", flush=True)
    print(f"done in {time.time() - t0:.0f}s; models: {sorted({m for g in gens.values() for m in g})}")


if __name__ == "__main__":
    main()
