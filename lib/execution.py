"""Driver for the sandboxed worker: every program runs in its own isolated Python process with a memory limit,
a per-call timeout and an overall budget, so that infinite loops or crashes of generated code cannot affect the
measurements. Results are streamed, so a process that has to be killed still returns the outcomes before the kill."""
import json
import os
import subprocess
import sys

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py")


def _invoke(req, timeout):
    p = subprocess.Popen([sys.executable, "-I", WORKER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True)
    try:
        out, _ = p.communicate(json.dumps(req), timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    return out


def run_program(src, calls, timeout=0.5, budget=30.0):
    """Outcome key of every call expression (TIMEOUT for calls that were not reached)."""
    if not calls:
        return []
    out = _invoke({"mode": "run", "src": src, "calls": calls, "timeout": timeout, "budget": budget}, budget + 15)
    res = ["TIMEOUT"] * len(calls)
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        if "load_error" in d:
            return ["LOAD:" + d["load_error"]] * len(calls)
        if isinstance(d.get("i"), int) and isinstance(d.get("k"), str) and 0 <= d["i"] < len(calls):
            res[d["i"]] = d["k"]
    return res


def eval_exprs(exprs):
    if not exprs:
        return []
    out = _invoke({"mode": "eval", "exprs": exprs}, 30 + len(exprs))
    try:
        return json.loads(out.strip().splitlines()[-1])
    except Exception:
        return ["EXC:EvalFailed"] * len(exprs)


def amplify(entry, calls, n, seed):
    if not calls:
        return []
    out = _invoke({"mode": "amplify", "entry": entry, "calls": calls, "n": n, "seed": seed}, 60)
    try:
        return json.loads(out.strip().splitlines()[-1])
    except Exception:
        return []


def coverage(src, calls, check_src=None, entry=None, timeout=0.5):
    req = {"mode": "coverage", "src": src, "calls": calls, "timeout": timeout}
    if check_src:
        req.update({"check": f"check({entry})", "check_src": check_src})
    out = _invoke(req, 60 + len(calls) * (timeout + 0.2) + (25 if check_src else 0))
    try:
        return json.loads(out.strip().splitlines()[-1])
    except Exception:
        return None


def check(src, check_src, entry, timeout=10.0):
    out = _invoke({"mode": "check", "src": src, "check_src": check_src, "entry": entry, "timeout": timeout}, timeout + 15)
    try:
        return json.loads(out.strip().splitlines()[-1])["k"]
    except Exception:
        return "TIMEOUT"
