"""First-order AST mutants of a reference program (classic operators of mutation testing; Jia & Harman, 2011).

Operators: arithmetic operator replacement (AOR), relational operator replacement (ROR), logical connector
replacement (LCR), unary/negation removal (UOR), constant replacement (CRP: integer +/-1, boolean flip, empty string),
augmented-assignment operator replacement (ASR), break/continue swap (BCR) and condition negation (CNI).
Only the body of the function under test (and functions nested in it) is mutated; docstrings are left untouched.
"""
import ast
import copy
import random

AOR = {ast.Add: [ast.Sub, ast.Mult], ast.Sub: [ast.Add], ast.Mult: [ast.Div, ast.Add], ast.Div: [ast.Mult, ast.FloorDiv],
       ast.FloorDiv: [ast.Div, ast.Mult], ast.Mod: [ast.FloorDiv], ast.Pow: [ast.Mult]}
ROR = {ast.Lt: [ast.LtE, ast.Gt], ast.LtE: [ast.Lt, ast.GtE], ast.Gt: [ast.GtE, ast.Lt], ast.GtE: [ast.Gt, ast.LtE],
       ast.Eq: [ast.NotEq], ast.NotEq: [ast.Eq], ast.In: [ast.NotIn], ast.NotIn: [ast.In], ast.Is: [ast.IsNot], ast.IsNot: [ast.Is]}


def _targets(tree, entry):
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == entry), None)
    if fn is None:
        return []
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    nodes = []
    for stmt in body:
        nodes.extend(ast.walk(stmt))
    return nodes


def _variants(node):
    """Yield (operator, mutate-function) pairs for one node; the function edits a deep copy in place."""
    if isinstance(node, ast.BinOp) and type(node.op) in AOR:
        for new in AOR[type(node.op)]:
            yield "AOR", lambda n, new=new: setattr(n, "op", new())
    if isinstance(node, ast.AugAssign) and type(node.op) in AOR:
        for new in AOR[type(node.op)][:1]:
            yield "ASR", lambda n, new=new: setattr(n, "op", new())
    if isinstance(node, ast.Compare):
        for i, op in enumerate(node.ops):
            for new in ROR.get(type(op), []):
                def f(n, i=i, new=new):
                    n.ops[i] = new()
                yield "ROR", f
    if isinstance(node, ast.BoolOp):
        yield "LCR", lambda n: setattr(n, "op", ast.Or() if isinstance(n.op, ast.And) else ast.And())
    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, bool):
            yield "CRP", lambda n: setattr(n, "value", not n.value)
        elif isinstance(v, int):
            yield "CRP", lambda n: setattr(n, "value", n.value + 1)
            yield "CRP", lambda n: setattr(n, "value", n.value - 1)
        elif isinstance(v, str) and v:
            yield "CRP", lambda n: setattr(n, "value", "")
    if isinstance(node, (ast.Break, ast.Continue)):
        yield "BCR", None
    if isinstance(node, (ast.If, ast.While)):
        yield "CNI", lambda n: setattr(n, "test", ast.UnaryOp(op=ast.Not(), operand=n.test))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub)):
        yield "UOR", None


def _replace(tree, old, new):
    for parent in ast.walk(tree):
        for name, val in ast.iter_fields(parent):
            if val is old:
                setattr(parent, name, new)
                return True
            if isinstance(val, list):
                for i, x in enumerate(val):
                    if x is old:
                        val[i] = new
                        return True
    return False


def mutants(src, entry, max_n=40, seed=2026):
    """Return a list of (operator, mutant source) for distinct, compilable mutants (random sample of size <= max_n)."""
    tree = ast.parse(src)
    base = ast.unparse(tree)
    targets = _targets(tree, entry)
    out, seen = [], {base}
    for idx, node in enumerate(targets):
        for j, (op, fn) in enumerate(_variants(node)):
            t2 = copy.deepcopy(tree)
            n2 = _targets(t2, entry)[idx]
            if op == "BCR":
                if not _replace(t2, n2, ast.Continue() if isinstance(n2, ast.Break) else ast.Break()):
                    continue
            elif op == "UOR":
                if not _replace(t2, n2, n2.operand):
                    continue
            else:
                fn(n2)
            try:
                ast.fix_missing_locations(t2)
                s = ast.unparse(t2)
                compile(s, "<mutant>", "exec")
            except Exception:
                continue
            if s not in seen:
                seen.add(s)
                out.append((op, s))
    rng = random.Random(seed)
    if len(out) > max_n:
        out = rng.sample(out, max_n)
    return out
