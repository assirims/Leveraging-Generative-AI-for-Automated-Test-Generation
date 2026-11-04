"""Step 2 - build the benchmark problems from the raw data.

HumanEval (Chen et al., 2021): 164 hand-written Python problems; specification = the prompt (signature + docstring),
reference = prompt + canonical solution, developer tests = the `check` function.
QuixBugs (Lin et al., 2017): Python programs with one real bug each and their corrected versions; we use the 31
programs that come with input/output test cases (the graph programs use custom node objects and are excluded).
Specification = signature + the program's docstring (moved inside the function), reference = corrected program,
buggy version = original program, developer tests = the JSON test cases.

Output: data/processed/problems.jsonl
"""
import ast
import gzip
import json
import os
import re

from config import PROC, RAW

HE = os.path.join(RAW, "human-eval", "data", "HumanEval.jsonl.gz")
QB = os.path.join(RAW, "QuixBugs")


def doc_examples(spec, entry):
    """Doctest-style examples (>>> call / expected line) from the specification, as (call, expected) source pairs."""
    out, lines = [], spec.splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith(">>>") and entry in s and i + 1 < len(lines):
            call = s[3:].strip()
            exp = lines[i + 1].strip()
            if exp and not exp.startswith(">>>") and not exp.startswith('"""'):
                out.append((call, exp))
    return out


def humaneval():
    probs = []
    for line in gzip.open(HE, "rt"):
        d = json.loads(line)
        spec = d["prompt"]
        probs.append({
            "pid": d["task_id"].replace("/", "_"), "bench": "HumanEval", "entry": d["entry_point"],
            "spec": spec, "ref_src": spec + d["canonical_solution"], "buggy_src": None,
            "human_check": d["test"], "human_io": None, "doc_examples": doc_examples(spec, d["entry_point"]),
        })
    return probs


def split_program(src):
    """Return (prefix imports, def line, body, docstring) of a QuixBugs program file."""
    tree = ast.parse(src)
    doc = None
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
            doc = node.value.value
    return tree, doc


def quixbugs():
    probs = []
    tdir = os.path.join(QB, "json_testcases")
    for fn in sorted(os.listdir(tdir)):
        name = fn[:-5]
        corr = open(os.path.join(QB, "correct_python_programs", name + ".py")).read()
        bug = open(os.path.join(QB, "python_programs", name + ".py")).read()
        _, doc = split_program(bug)
        tree = ast.parse(corr)
        fdef = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        imports = [ast.get_source_segment(corr, n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        sig = corr.splitlines()[fdef.lineno - 1].rstrip()
        doc = (doc or "").strip("\n")
        doc = "\n".join(("    " + l if l.strip() else "") for l in doc.splitlines())
        spec = ("\n".join(imports) + "\n\n" if imports else "") + f'{sig}\n    """\n{doc}\n    """\n'
        # reference/buggy modules: strip the trailing module docstrings so that only code remains
        def code_only(src):
            t = ast.parse(src)
            t.body = [n for n in t.body if not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant))]
            return ast.unparse(t) + "\n"
        io = []
        for ln in open(os.path.join(tdir, fn)):
            ln = ln.strip()
            if ln:
                args, exp = json.loads(ln)
                io.append([args if isinstance(args, list) else [args], exp])
        probs.append({
            "pid": "QuixBugs_" + name, "bench": "QuixBugs", "entry": name, "spec": spec,
            "ref_src": code_only(corr), "buggy_src": code_only(bug), "human_check": None, "human_io": io,
            "doc_examples": doc_examples(spec, name),
        })
    return probs


def main():
    probs = humaneval() + quixbugs()
    with open(os.path.join(PROC, "problems.jsonl"), "w") as fh:
        for p in probs:
            fh.write(json.dumps(p) + "\n")
    n_doc = sum(1 for p in probs if p["doc_examples"])
    print(f"{len(probs)} problems ({sum(p['bench'] == 'HumanEval' for p in probs)} HumanEval, "
          f"{sum(p['bench'] == 'QuixBugs' for p in probs)} QuixBugs); {n_doc} with doctest examples")


if __name__ == "__main__":
    main()
