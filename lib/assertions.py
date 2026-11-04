"""Parsing of model outputs: assertions written by the model (direct oracles) and spec-derived implementations."""
import ast
import math
import textwrap


def _strip_wrappers(node, entry):
    """list(f(..)) / tuple(f(..)) / sorted(f(..)) / set(f(..)) around the call under test -> the call itself."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == entry:
        return node, None
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("list", "tuple", "sorted", "set")
            and len(node.args) == 1 and not node.keywords):
        inner, _ = _strip_wrappers(node.args[0], entry)
        if inner is not None:
            return inner, node.func.id
    return None, None


def parse_assertion(line, entry):
    """Return (call_src, expected_src, wrapper) for `assert f(args) == expected` and simple variants, else None."""
    s = line.strip()
    if not s.startswith("assert"):
        return None
    try:
        node = ast.parse(s).body[0]
    except SyntaxError:
        return None
    if not isinstance(node, ast.Assert):
        return None
    t = node.test
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], (ast.Eq, ast.Is)):
        left, right = t.left, t.comparators[0]
        call, wrap = _strip_wrappers(left, entry)
        if call is None:
            call, wrap = _strip_wrappers(right, entry)
            left, right = right, left
        if call is None:
            return None
        if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == entry for n in ast.walk(right)):
            return None
        return ast.unparse(call), ast.unparse(right), wrap
    call, wrap = _strip_wrappers(t, entry)
    if call is not None:
        return ast.unparse(call), "True", wrap
    if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
        call, wrap = _strip_wrappers(t.operand, entry)
        if call is not None:
            return ast.unparse(call), "False", wrap
    return None


def parse_tests(text, entry, probs=None):
    """Parse the model's test answer into assertions with a token-level confidence of the expected value.

    probs: list of (token, logprob) for the generated text (greedy decoding); the confidence of an assertion is the
    minimum token probability over the characters of its expected-value expression (and its mean log-probability)."""
    offsets = []
    if probs:
        pos = 0
        for tok, lp in probs:
            tok = tok or ""
            offsets.append((pos, pos + len(tok), lp if lp is not None else 0.0))
            pos += len(tok)
    out, n_lines, pos = [], 0, 0
    for line in text.split("\n"):
        start = pos
        pos += len(line) + 1
        if not line.strip().startswith("assert"):
            continue
        n_lines += 1
        r = parse_assertion(line, entry)
        if r is None:
            continue
        call, exp, wrap = r
        conf_min, conf_mean = None, None
        if offsets:
            # locate the expected-value span: text after the last top-level '==' (or the whole line for bare calls)
            idx = line.rfind("==")
            a = start + (idx + 2 if idx >= 0 else 0)
            b = start + len(line)
            lps = [lp for (x, y, lp) in offsets if y > a and x < b]
            if lps:
                conf_min = math.exp(min(lps))
                conf_mean = sum(lps) / len(lps)
        out.append({"call": call, "expected": exp, "wrap": wrap, "line": line.strip(), "conf_min": conf_min, "conf_mean": conf_mean})
    return out, n_lines


def assemble(spec, text):
    """Program source from the specification and the generated body (prefill was the spec plus 4 spaces).

    Small models sometimes add one space to the indentation of the generated block; the block is then re-indented
    to the function's indentation. Returns (source, compiles)."""
    spec = spec if spec.endswith("\n") else spec + "\n"
    cands = ["    " + text]
    if text.startswith(" "):
        cands.append("    " + text[1:])
    body = textwrap.dedent("    " + text)
    cands.append(textwrap.indent(body, "    ", lambda l: True))
    for c in cands:
        src = spec + c.rstrip() + "\n"
        try:
            compile(src, "<impl>", "exec")
            return src, True
        except SyntaxError:
            continue
    return spec + "    " + text.rstrip() + "\n", False
