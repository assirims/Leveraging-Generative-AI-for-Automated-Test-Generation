"""Step 2b - build the BioMedFn benchmark (biomedical and clinical functions) from its source definitions.

BioMedFn contains small, self-contained Python functions of four biomedical domains (clinical scores and decision
support; anthropometrics, renal function and precision dosing; genomics and multi-omics; physiological signals and
wearables), written for this study from published formulas (data/raw/biomedfn/*.py). For each function:
  specification  signature + docstring (formula, units, rounding, error conditions) + two worked examples whose
                 outputs are computed from the reference;
  reference      the correct implementation (spec + body);
  domain fault   one hand-seeded realistic fault (unit or coefficient error, boundary, sign, branch, missing bound or
                 check, ...), stored as `buggy_src` like the real bugs of QuixBugs;
  developer tests input/output cases whose expected outputs are computed from the reference.
Quality checks: the reference compiles and runs on every example and test input; every fault compiles, differs from
the reference and is detected by at least one developer test.

Output: data/processed/problems_biomed.jsonl, results/tables/biomed/biomed_benchmark_catalog.csv,
        data/raw/biomedfn/MANIFEST.json (SHA-256 of the source files)
"""
import csv
import hashlib
import importlib.util
import json
import os
import textwrap

from config import MAX_MUTANTS, PROC, RAW, RESULTS, SEED
from lib.mutation import mutants

TABLES = os.path.join(RESULTS, "tables", "biomed")
os.makedirs(TABLES, exist_ok=True)

SRC = os.path.join(RAW, "biomedfn")
FAULT_CATEGORY = {   # seeded fault class -> category reported in the paper
    "unit": "unit or scale", "hard-coded": "unit or scale",
    "coefficient": "coefficient or constant", "version": "coefficient or constant", "weight": "coefficient or constant",
    "table entry": "coefficient or constant", "exponent": "coefficient or constant",
    "boundary": "threshold or boundary", "range": "threshold or boundary", "bound": "threshold or boundary",
    "formula": "formula or estimator", "log base": "formula or estimator", "estimator": "formula or estimator",
    "denominator": "formula or estimator", "gap handling": "formula or estimator", "operation set": "formula or estimator",
    "branch": "logic or indexing", "swap": "logic or indexing", "sign": "logic or indexing", "tie-break": "logic or indexing",
    "case": "logic or indexing", "frame": "logic or indexing", "off-by-one": "logic or indexing",
    "omission": "missing step or safeguard", "missing bound": "missing step or safeguard", "missing cap": "missing step or safeguard",
    "missing check": "missing step or safeguard", "missing clamp": "missing step or safeguard", "missing data": "missing step or safeguard",
    "missing monotonicity": "missing step or safeguard",
}
DOMAINS = [("clinical", "Clinical scores and decision support"), ("dosing", "Renal function and precision dosing"),
           ("omics", "Genomics and multi-omics"), ("biosignal", "Physiological signals and wearables")]


def load(domain):
    spec = importlib.util.spec_from_file_location(f"biomedfn_{domain}", os.path.join(SRC, domain + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.PROBLEMS


def call_src(entry, args):
    return f"{entry}({', '.join(repr(a) for a in args)})"


def run(src, entry, args):
    """Execute trusted benchmark code in-process (the benchmark is our own source, not model output)."""
    ns = {}
    exec(compile(src, f"<{entry}>", "exec"), ns)
    try:
        return ("ok", ns[entry](*json.loads(json.dumps(args))))
    except Exception as e:  # noqa: BLE001 - the reference may raise by specification
        return ("exc", type(e).__name__)


def build_one(d, domain):
    entry = d["entry"]
    imports = d.get("imports", "")
    body = textwrap.dedent(d["body"]).strip("\n") + "\n"
    head = (imports + "\n\n\n" if imports else "") + d["sig"] + "\n"
    doc = textwrap.dedent(d["doc"]).strip("\n")

    def assemble(doc_text, body_text):
        ind = "\n".join(("    " + l if l.strip() else "") for l in doc_text.splitlines())
        return head + '    """\n' + ind + '\n    """\n' + textwrap.indent(body_text, "    ")

    plain = assemble(doc, body)
    ex_lines = []
    for args in d["examples"]:
        st, v = run(plain, entry, args)
        assert st == "ok", (entry, args, v)
        ex_lines.append(f">>> {call_src(entry, args)}\n{v!r}")
    full_doc = doc + "\n\nExamples:\n" + "\n".join(ex_lines)
    spec = head + '    """\n' + "\n".join(("    " + l if l.strip() else "") for l in full_doc.splitlines()) + '\n    """\n'
    ref = spec + textwrap.indent(body, "    ")
    old, new, fclass = d["fault"]
    assert body.count(old) == 1, (entry, "fault anchor must occur once", old)
    buggy = spec + textwrap.indent(body.replace(old, new), "    ")
    compile(ref, entry, "exec")
    compile(buggy, entry, "exec")
    io, detected, on_valid = [], False, False
    for args in d["tests"]:
        st, v = run(ref, entry, args)
        sb, vb = run(buggy, entry, args)
        if (st, repr(v)) != (sb, repr(vb)):
            detected = True
            on_valid = on_valid or st == "ok"
        io.append([args, v if st == "ok" else {"raises": v}])
    for args in d["examples"]:
        assert run(ref, entry, args)[0] == "ok"
    assert detected, (entry, "the developer tests do not detect the seeded fault")
    json.dumps(io)
    doc_examples = [(call_src(entry, a), repr(run(ref, entry, a)[1])) for a in d["examples"]]
    return {"pid": "BioMed_" + entry, "bench": "BioMed", "entry": entry, "spec": spec, "ref_src": ref, "buggy_src": buggy,
            "human_check": None, "human_io": io, "doc_examples": doc_examples,
            "domain": domain, "topic": d["topic"], "source": d["source"], "fault_class": fclass, "fault_category": FAULT_CATEGORY[fclass],
            "fault_on_valid_input": on_valid, "n_mutants": len(mutants(ref, entry, MAX_MUTANTS, SEED))}


def main():
    probs, rows = [], []
    for domain, label in DOMAINS:
        for d in load(domain):
            p = build_one(d, domain)
            probs.append(p)
            rows.append({"pid": p["pid"], "entry": p["entry"], "domain": domain, "domain_label": label, "topic": p["topic"],
                         "source": p["source"], "fault_class": p["fault_class"], "fault_category": p["fault_category"], "fault_on_valid_input": p["fault_on_valid_input"],
                         "mutants": p["n_mutants"], "developer_tests": len(p["human_io"]),
                         "spec_lines": p["spec"].count("\n")})
    names = [p["entry"] for p in probs]
    assert len(names) == len(set(names)), "duplicate entry points"
    with open(os.path.join(PROC, "problems_biomed.jsonl"), "w") as fh:
        for p in probs:
            fh.write(json.dumps(p) + "\n")
    with open(os.path.join(TABLES, "biomed_benchmark_catalog.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    man = {"benchmark": "BioMedFn", "files": {}}
    for domain, _ in DOMAINS:
        f = os.path.join(SRC, domain + ".py")
        man["files"][domain + ".py"] = {"sha256": hashlib.sha256(open(f, "rb").read()).hexdigest(), "bytes": os.path.getsize(f)}
    json.dump(man, open(os.path.join(SRC, "MANIFEST.json"), "w"), indent=1)
    by = {dm: sum(p["domain"] == dm for p in probs) for dm, _ in DOMAINS}
    print(f"BioMedFn: {len(probs)} problems {by}; developer tests: {sum(r['developer_tests'] for r in rows)}; mutants: "
          f"{sum(r['mutants'] for r in rows)}; faults visible on a valid input: {sum(r['fault_on_valid_input'] for r in rows)}; "
          f"fault categories: { {c: sum(p['fault_category'] == c for p in probs) for c in sorted(set(FAULT_CATEGORY.values()))} }")


if __name__ == "__main__":
    main()
