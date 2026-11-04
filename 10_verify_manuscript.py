"""Step 10 - check the Word manuscript against the results:
  * key numbers of the abstract and of the main result tables (including the high-probability analysis) appear,
  * every listed reference is cited and every cited number is listed,
  * the manuscript has no appendix: every figure and table is in the main text, numbered consecutively in the order
    of placement, cited in the text before its caption, and first cited in numerical order."""
import json
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

import docx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import RESULTS, TEST_MODELS  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))


def fx(x, d=2):
    return str(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def pct(x, d=0):
    return fx(100 * float(x), d) + "%"


def main():
    N = json.load(open(os.path.join(RESULTS, "paper_numbers.json")))
    path = os.path.join(ROOT, "manuscript", "CORAL_Manuscript.docx")      # freshly built
    if not os.path.exists(path):
        path = os.path.join(ROOT, "00_PAPER", "CORAL_Manuscript.docx")    # as shipped in the replication package
    if not os.path.exists(path):
        sys.exit("earlier general-code manuscript not built: run  cd manuscript && node build_manuscript.js  first")
    d = docx.Document(path)
    paras = [p.text for p in d.paragraphs]
    tables = "\n".join(" | ".join(c.text for c in r.cells) for t in d.tables for r in t.rows)
    txt = "\n".join(paras) + "\n" + tables
    big = TEST_MODELS[-1]
    M = lambda m, a=None: next(r for r in N["methods"] if r["method"] == m and r["bench"] == "All" and r["alpha"] == a)
    D = N["data"]
    checks = [("problems", str(D["n_problems"])), ("real faults", str(D["real_faults"])), ("LLM faults", str(D["llm_faults"])),
              ("killable mutants", f"{D['killable_mutants']:,}")]
    for meth, a in ((f"CORAL|{big}", 0.1), (f"Direct+conf|{big}", 0.1), (f"Direct|{big}", None), ("CORAL-hetero", 0.1)):
        r = M(meth, a)
        checks += [(f"{meth} FA", pct(r["fa"], 1)), (f"{meth} real", pct(r["det_real"])), (f"{meth} LLM", pct(r["det_llm"])),
                   (f"{meth} mutation", fx(r["mut_score"]))]
    for r in N["paired"]:
        if r["alpha"] == 0.1 and r["measure"] == "detection_real_llm" and r["comparison"].startswith("Qwen2.5-3B: Direct + confidence"):
            checks += [("paired detection CORAL", pct(r["rate_B"], 1)), ("paired detection conf", pct(r["rate_A"], 1))]
    for r in N["crc"]:
        if r["bench"] == "All" and r["method"] in (f"CORAL|{m}" for m in TEST_MODELS):
            checks.append((f"{r['method']} CRC FA α={r['alpha']}", f"{fx(r['fa_mean'], 3)} ± {fx(r['fa_sd'], 3)}"))
    H = {(r["method"], r["alpha"], r["procedure"]): r for r in N["high_probability"]}
    for (meth, a, proc), r in H.items():     # every cell of the high-probability table
        if (meth, a, "CRC") in H and (meth, a, "LTT") in H and proc == "LTT":
            c = H[(meth, a, "CRC")]
            checks += [(f"HP {meth} α={a} FA", f"{fx(c['fa_mean'], 3)} / {fx(r['fa_mean'], 3)}"),
                       (f"HP {meth} α={a} q90", f"{fx(c['fa_q90'], 3)} / {fx(r['fa_q90'], 3)}"),
                       (f"HP {meth} α={a} mutation", f"{fx(c['mut_score'])} / {fx(r['mut_score'])}")]
    hl, hq = H[(f"CORAL|{big}", 0.1, "LTT")], H[(f"Direct+conf|{big}", 0.1, "CRC")]
    checks += [("abstract HP CORAL mutation", f"mean mutation score ({fx(hl['mut_score'])})"), ("abstract HP conf mutation", f"weaker one ({fx(hq['mut_score'])})")]
    for r in N["worked_example"]:
        checks.append((f"worked example {r['call']}", r["call"][r["call"].index("("):]))
    ok = 0
    for lab, s in checks:
        found = s in txt
        ok += found
        if not found:
            print("NOT FOUND:", lab, s)

    # references
    joined = "\n".join(paras)
    body, _, refs = joined.partition("\nReferences\n")
    no_appendix = not re.search(r"Appendix|Table [A-Z]\d|Supplementary (Table|Fig)", txt)
    cited = set()
    for m in re.finditer(r"\[(\d[\d,–]*)\]", body + "\n" + tables):
        for part in m.group(1).split(","):
            if "–" in part:
                a, b = map(int, part.split("–"))
                cited.update(range(a, b + 1))
            elif part:
                cited.add(int(part))
    n_refs = len(re.findall(r"^\[\d+\]\t", refs, flags=re.M))
    MAX_REFS = 30                                       # journal-facing limit chosen by the authors

    # figures and tables cited before their caption (paragraph order of the document body)
    n_fig = len([p for p in paras if re.match(r"Fig\. \d+\. ", p)])
    n_tab = len([p for p in paras if re.match(r"Table \d+\n", p)])
    labels = [f"Fig. {i}" for i in range(1, n_fig + 1)] + [f"Table {i}" for i in range(1, n_tab + 1)]
    order_bad, firsts, caps = [], {"Fig": [], "Table": []}, {"Fig": [], "Table": []}
    for lab in labels:
        capre = re.compile(re.escape(lab) + (r"\n" if lab.startswith("Table") else r"\. "))
        cap = next((i for i, p in enumerate(paras) if capre.match(p)), None)
        pat = re.compile(re.escape(lab) + r"(?![0-9])|" + (r"Tables " + lab.split()[-1] + r" and \d+" if lab.startswith("Table") else r"$^"))
        first = next((i for i, p in enumerate(paras) if pat.search(p) and not capre.match(p)), None)
        if first is None:   # first citation may be in the caption of an earlier display item
            first = next((i for i, p in enumerate(paras) if pat.search(p.split("\n", 1)[-1]) and not capre.match(p)), None)
        if cap is None or first is None or first > cap:
            order_bad.append((lab, first, cap))
        firsts[lab.split()[0].rstrip(".")].append(first if first is not None else -1)
        caps[lab.split()[0].rstrip(".")].append(cap if cap is not None else -1)
    mono = lambda xs: all(a <= b for a, b in zip(xs, xs[1:]))
    numbering_ok = all(mono(caps[k]) and mono(firsts[k]) for k in caps)

    print(f"{ok}/{len(checks)} key numbers found in {os.path.relpath(path, ROOT)}; references listed: {n_refs}; "
          f"distinct numbers cited: {len(cited)}; figures/tables cited before their caption: {len(labels) - len(order_bad)}/{len(labels)} "
          f"({n_fig} figures, {n_tab} tables); numbered in order of placement and first citation: {numbering_ok}; no appendix: {no_appendix}")
    missing = sorted(set(range(1, n_refs + 1)) - cited)
    if missing:
        print("listed but not cited:", missing)
    if order_bad:
        print("not cited before caption:", order_bad)
    print(f"reference list: {n_refs} entries (maximum {MAX_REFS})")
    if ok < len(checks) or cited != set(range(1, n_refs + 1)) or order_bad or not numbering_ok or not no_appendix or n_refs > MAX_REFS:
        sys.exit(1)


if __name__ == "__main__":
    main()
