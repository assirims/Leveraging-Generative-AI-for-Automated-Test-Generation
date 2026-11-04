"""Tests of the sandboxed execution, outcome canonicalisation, assertion parsing and mutation operators.

Run:  python3 -m pytest tests   (or: python3 tests/test_execution.py)"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.assertions import parse_assertion  # noqa: E402
from lib.execution import run_program  # noqa: E402
from lib.mutation import mutants  # noqa: E402

SRC = """
def f(x):
    print("noise on stdout")
    if x == 'loop':
        while True:
            pass
    if x == 'err':
        raise ValueError('bad')
    if x == 'float':
        return 0.1 + 0.2
    if x == 'set':
        return {3, 1, 2}
    if x == 'tuple':
        return (1, 2)
    if x == 'gen':
        return (i for i in range(3))
    return [1, 2]
"""


def test_outcomes_are_canonical_and_isolated():
    calls = ["f('list')", "f('tuple')", "f('err')", "f('loop')", "f('float')", "f('set')", "f('gen')", "f('list')"]
    out = run_program(SRC, calls, timeout=0.5, budget=10.0)
    assert len(out) == len(calls)
    assert out[0] != out[1]                                  # lists and tuples are distinguished
    assert out[2].startswith("EXC:ValueError")
    assert out[3] == "TIMEOUT"                               # infinite loop stopped by the per-call limit
    float_ok = run_program("def g():\n    return 0.3\n", ["g()"])[0]
    assert out[4] == float_ok                                # 0.1 + 0.2 == 0.3 after rounding to 9 significant digits
    set_ok = run_program("def g():\n    return {1, 2, 3}\n", ["g()"])[0]
    assert out[5] == set_ok                                  # sets are order-free
    assert out[6] == run_program("def g():\n    return [0, 1, 2]\n", ["g()"])[0]   # generators are consumed
    assert out[7] == out[0]                                  # later calls still run after a time-out


def test_numbers_compare_numerically():
    a = run_program("def g():\n    return 1\n", ["g()"])[0]
    b = run_program("def g():\n    return 1.0\n", ["g()"])[0]
    c = run_program("def g():\n    return True\n", ["g()"])[0]
    assert a == b == c                                       # Python equality: 1 == 1.0 == True


def test_load_error_reported():
    out = run_program("def g(:\n", ["g()"])
    assert out[0].startswith("LOAD:")


def test_parse_assertion_variants():
    assert parse_assertion("assert f(1, [2]) == 3", "f") == ("f(1, [2])", "3", None) or parse_assertion("assert f(1, [2]) == 3", "f")[:2] == ("f(1, [2])", "3")
    assert parse_assertion("assert 3 == f(1)", "f")[:2] == ("f(1)", "3")
    assert parse_assertion("assert f('a') is True", "f")[:2] == ("f('a')", "True")
    assert parse_assertion("assert not f(0)", "f")[:2] == ("f(0)", "False")
    assert parse_assertion("assert g(1) == 2", "f") is None
    assert parse_assertion("assert f(1) == f(2)", "f") is None


def test_mutants_are_distinct_and_compile():
    src = "def h(a, b):\n    s = 0\n    for i in range(a):\n        if i % 2 == 0 and b > 0:\n            s += i * b\n        else:\n            break\n    return s - 1\n"
    M = mutants(src, "h", max_n=40, seed=2026)
    assert 5 <= len(M) <= 40
    srcs = [m for _, m in M]
    assert len(set(srcs)) == len(srcs)
    for s in srcs:
        compile(s, "<m>", "exec")
    ops = {op for op, _ in M}
    assert {"AOR", "ROR"} <= ops


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
