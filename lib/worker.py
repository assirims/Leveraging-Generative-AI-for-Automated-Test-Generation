"""Sandboxed execution worker (run as a separate `python -I` process; reads one JSON request from stdin).

Modes
  run       execute one program on a list of call expressions; one JSON line per call is streamed to stdout
            with the canonical outcome (value, exception type or timeout)
  eval      evaluate literal expressions (expected values of assertions) to canonical keys
  amplify   derive new inputs from call expressions by type-aware mutation of the argument values
  coverage  per call: executed lines and branch outcomes of the program (sys.monitoring)
  check     run a HumanEval `check(candidate)` function against the program

Canonical outcomes follow Python's == semantics closely: bool/int/integral floats compare as numbers, floats are
rounded to 9 significant digits, lists and tuples are distinguished, sets and dicts are order-free, generators are
consumed into lists. Exceptions are recorded by type, timeouts as TIMEOUT.
"""
import ast
import io
import json
import math
import os
import random
import resource
import signal
import sys
import types

CALL_TIMEOUT = 0.5


class _Timeout(BaseException):
    pass


def _alarm(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _alarm)


def canon(v, depth=0):
    if depth > 20:
        return ("deep",)
    if v is None:
        return ("N",)
    if isinstance(v, bool):
        return ("n", int(v))
    if isinstance(v, int):
        return ("n", v) if abs(v) < 10 ** 30 else ("bigint", str(v)[:60], len(str(v)))
    if isinstance(v, float):
        if math.isnan(v):
            return ("nan",)
        if math.isinf(v):
            return ("inf", v > 0)
        if v == int(v) and abs(v) < 1e15:
            return ("n", int(v))
        return ("f", float(f"{v:.9g}"))
    if isinstance(v, complex):
        return ("c", float(f"{v.real:.9g}"), float(f"{v.imag:.9g}"))
    if isinstance(v, str):
        return ("s", v if len(v) <= 2000 else v[:2000] + f"...{len(v)}")
    if isinstance(v, (bytes, bytearray)):
        return ("b", bytes(v)[:2000].hex())
    if isinstance(v, list):
        return ("L", tuple(canon(x, depth + 1) for x in v[:5000]), len(v))
    if isinstance(v, tuple):
        return ("T", tuple(canon(x, depth + 1) for x in v[:5000]), len(v))
    if isinstance(v, (set, frozenset)):
        return ("S", tuple(sorted((canon(x, depth + 1) for x in v), key=repr)))
    if isinstance(v, dict):
        return ("D", tuple(sorted(((canon(k, depth + 1), canon(x, depth + 1)) for k, x in v.items()), key=repr)))
    if isinstance(v, (types.GeneratorType, map, filter, zip, range, reversed)) or (hasattr(v, "__next__") and hasattr(v, "__iter__")):
        out = []
        for x in v:
            out.append(x)
            if len(out) > 5000:
                break
        return canon(out, depth)
    return ("o", type(v).__name__, repr(v)[:200])


def key(v):
    return repr(canon(v))


def limit_resources():
    try:
        resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    except Exception:
        pass
    sys.setrecursionlimit(3000)


def load(src):
    ns = {"__name__": "__program__"}
    code = compile(src, "<program>", "exec")
    old = sys.stdout
    sys.stdout = io.StringIO()            # programs must not write to the result stream
    signal.setitimer(signal.ITIMER_REAL, 2.0)
    try:
        exec(code, ns)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        sys.stdout = old
    return ns


def call(ns, expr, timeout):
    """Evaluate a call expression in the program namespace; return the canonical outcome key."""
    out_buf = io.StringIO()
    old = sys.stdout
    sys.stdout = out_buf
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        v = eval(expr, ns)
        k = key(v)
    except _Timeout:
        k = "TIMEOUT"
    except RecursionError:
        k = "EXC:RecursionError"
    except MemoryError:
        k = "EXC:MemoryError"
    except BaseException as e:  # noqa: BLE001 - any failure of the program is an outcome
        k = "EXC:" + type(e).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        sys.stdout = old
    return k


def mode_run(req):
    timeout = req.get("timeout", CALL_TIMEOUT)
    try:
        ns = load(req["src"])
    except BaseException as e:  # noqa: BLE001
        print(json.dumps({"load_error": type(e).__name__}), flush=True)
        return
    n_to, budget = 0, req.get("budget", 30.0)
    import time
    t0 = time.time()
    for i, expr in enumerate(req["calls"]):
        if n_to >= 3 or time.time() - t0 > budget:
            k = "TIMEOUT"
        else:
            k = call(ns, expr, timeout)
            n_to += k == "TIMEOUT"
        print(json.dumps({"i": i, "k": k}), flush=True)


def mode_eval(req):
    out = []
    for e in req["exprs"]:
        signal.setitimer(signal.ITIMER_REAL, 1.0)
        try:
            out.append(key(eval(e, {"__builtins__": __builtins__})))
        except BaseException as ex:  # noqa: BLE001
            out.append("EXC:" + type(ex).__name__)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(out), flush=True)


# ---------------------------------------------------------------- input amplification
def _roundtrip(v):
    try:
        return eval(repr(v)) == v and len(repr(v)) <= 400
    except BaseException:  # noqa: BLE001
        return False


def mutate_value(v, rng, depth=0):
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        c = rng.choice([v + 1, v - 1, -v, 0, 2 * v, v // 2, v + rng.randint(2, 9), 1])
        return max(-10 ** 6, min(10 ** 6, c))
    if isinstance(v, float):
        return rng.choice([v + 1.0, v - 0.5, -v, 0.0, v * 2, v / 3, round(v, 1) + 0.25])
    if isinstance(v, str):
        ops = ["", v[::-1], v + v[:1], v[1:], v.upper(), v.lower(), v.swapcase(), v + " ", " " + v]
        if v:
            i = rng.randrange(len(v))
            ops += [v[:i] + v[i] + v[i:], v[:i] + v[i + 1:], v[:i] + rng.choice(v) + v[i + 1:]]
        return rng.choice(ops)[:200]
    if isinstance(v, list):
        ops = [lambda: [], lambda: v[::-1], lambda: v[:-1], lambda: v + v[:1], lambda: v + v]
        if v:
            def one():
                w = list(v)
                i = rng.randrange(len(w))
                w[i] = mutate_value(w[i], rng, depth + 1)
                return w
            ops += [one, one, lambda: rng.sample(v, len(v))]
            try:
                sorted(v)
                ops.append(lambda: sorted(v))
            except TypeError:
                pass
        return rng.choice(ops)()[:50]
    if isinstance(v, tuple):
        return tuple(mutate_value(list(v), rng, depth + 1))
    if isinstance(v, dict):
        if not v:
            return v
        w = dict(v)
        k = rng.choice(list(w))
        if rng.random() < 0.3:
            del w[k]
        else:
            w[k] = mutate_value(w[k], rng, depth + 1)
        return w
    if isinstance(v, set):
        return set(mutate_value(sorted(v, key=repr), rng, depth + 1))
    return v


def mode_amplify(req):
    entry, n, rng = req["entry"], req["n"], random.Random(req["seed"])
    base = []
    for c in req["calls"]:
        try:
            node = ast.parse(c, mode="eval").body
            args = [eval(compile(ast.Expression(a), "<a>", "eval")) for a in node.args]
            kws = {k.arg: eval(compile(ast.Expression(k.value), "<a>", "eval")) for k in node.keywords}
            base.append((args, kws))
        except BaseException:  # noqa: BLE001
            continue
    seen = {key((a, k)) for a, k in base}
    out, tries = [], 0
    while base and len(out) < n and tries < 50 * n:
        tries += 1
        a, k = rng.choice(base)
        a, k = list(a), dict(k)
        slots = [("a", i) for i in range(len(a))] + [("k", x) for x in k]
        if not slots:
            break
        for _ in range(1 if rng.random() < 0.7 else 2):
            t, s = rng.choice(slots)
            if t == "a":
                a[s] = mutate_value(a[s], rng)
            else:
                k[s] = mutate_value(k[s], rng)
        if not all(_roundtrip(x) for x in a + list(k.values())):
            continue
        kk = key((a, k))
        if kk in seen:
            continue
        seen.add(kk)
        parts = [repr(x) for x in a] + [f"{x}={repr(y)}" for x, y in k.items()]
        out.append(f"{entry}({', '.join(parts)})")
    print(json.dumps(out), flush=True)


# ---------------------------------------------------------------- coverage
def _code_objects(code):
    out = []
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            out.append(c)
            out.extend(_code_objects(c))
    return out


BRANCH_OPS = {"POP_JUMP_IF_FALSE", "POP_JUMP_IF_TRUE", "POP_JUMP_IF_NONE", "POP_JUMP_IF_NOT_NONE", "FOR_ITER"}


def mode_coverage(req):
    import dis
    src = req["src"]
    mod_code = compile(src, "<program>", "exec")
    funcs = [c for c in _code_objects(mod_code) if c.co_filename == "<program>"]
    lines, branches = set(), set()
    for c in funcs:
        for _, _, ln in c.co_lines():
            if ln is not None and ln != c.co_firstlineno:
                lines.add(ln)
        for ins in dis.get_instructions(c):
            if ins.opname in BRANCH_OPS:
                branches.add((c.co_qualname, ins.offset))
    ns = {"__name__": "__program__"}
    signal.setitimer(signal.ITIMER_REAL, 2.0)
    exec(mod_code, ns)
    signal.setitimer(signal.ITIMER_REAL, 0)
    mon = sys.monitoring
    tool = mon.COVERAGE_ID
    mon.use_tool_id(tool, "coral")
    hit_l, hit_b = set(), set()

    def on_line(code, line):
        if code.co_filename == "<program>":
            hit_l.add(line)

    def on_branch(code, off, dest):
        if code.co_filename == "<program>":
            hit_b.add((code.co_qualname, off, dest))

    mon.register_callback(tool, mon.events.LINE, on_line)
    mon.register_callback(tool, mon.events.BRANCH, on_branch)
    per_call = []
    exprs = req["calls"] + ([req["check"]] if req.get("check") else [])
    if req.get("check"):
        exec(compile(req["check_src"], "<check>", "exec"), ns)
    for expr in exprs:
        hit_l.clear()
        hit_b.clear()
        mon.set_events(tool, mon.events.LINE | mon.events.BRANCH)
        mon.restart_events()
        old = sys.stdout
        sys.stdout = io.StringIO()
        signal.setitimer(signal.ITIMER_REAL, req.get("timeout", CALL_TIMEOUT) if expr != req.get("check") else 20.0)
        try:
            v = eval(expr, ns)
            canon(v)
        except BaseException:  # noqa: BLE001
            pass
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            sys.stdout = old
            mon.set_events(tool, 0)
        per_call.append({"l": sorted(hit_l & lines), "b": sorted([f"{q}:{o}:{d}" for q, o, d in hit_b if (q, o) in branches])})
    print(json.dumps({"n_lines": len(lines), "n_branches": 2 * len(branches), "calls": per_call}), flush=True)


def mode_check(req):
    try:
        ns = load(req["src"])
        exec(compile(req["check_src"], "<check>", "exec"), ns)
    except BaseException as e:  # noqa: BLE001
        print(json.dumps({"k": "LOAD:" + type(e).__name__}), flush=True)
        return
    old = sys.stdout
    sys.stdout = io.StringIO()
    signal.setitimer(signal.ITIMER_REAL, req.get("timeout", 10.0))
    try:
        ns["check"](ns[req["entry"]])
        k = "PASS"
    except _Timeout:
        k = "TIMEOUT"
    except AssertionError:
        k = "FAIL"
    except BaseException as e:  # noqa: BLE001
        k = "EXC:" + type(e).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        sys.stdout = old
    print(json.dumps({"k": k}), flush=True)


if __name__ == "__main__":
    limit_resources()
    req = json.loads(sys.stdin.read())
    CALL_TIMEOUT = req.get("timeout", CALL_TIMEOUT)
    {"run": mode_run, "eval": mode_eval, "amplify": mode_amplify, "coverage": mode_coverage, "check": mode_check}[req["mode"]](req)
