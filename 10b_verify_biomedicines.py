"""Step 10b - check the Biomedicines manuscript (manuscript_biomed/CORAL_Biomedicines_Manuscript.docx):
  * at most 30 references, every listed reference cited, every cited number listed;
  * no appendix; figures and tables numbered consecutively in the order of placement, each cited before it appears
    (or in an earlier caption) and first cited in numerical order;
  * key numbers of the general-code suite (and, once available, of the biomedical suite) appear in the text;
  * abstract length; number of PENDING markers (must be 0 with --final, i.e. after the models have been run).
Usage: python 10b_verify_biomedicines.py [--final]
"""
import json
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

import docx

ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_REFS = 30


def fx(x, d=2):
    return str(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def pct(x, d=0):
    return str((Decimal(repr(float(x))) * 100).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)) + "%"


def main():
    final = "--final" in sys.argv
    path = os.path.join(ROOT, "manuscript_biomed", "CORAL_Biomedicines_Manuscript.docx")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "00_PAPER", "CORAL_Biomedicines_Manuscript.docx")
    d = docx.Document(path)
    paras = [p.text for p in d.paragraphs]
    tables = "\n".join(" | ".join(c.text for c in r.cells) for t in d.tables for r in t.rows)
    txt = "\n".join(paras) + "\n" + tables
    problems = []
    # ---------------------------------------------------------------- references
    joined = "\n".join(paras)
    body, _, refs = joined.partition("\nReferences\n")
    n_refs = len(re.findall(r"^\d+\.\t", refs, flags=re.M))
    cited = set()
    for m in re.finditer(r"\[(\d[\d,–]*)\]", body + "\n" + tables):
        for part in m.group(1).split(","):
            if "–" in part:
                a, b = map(int, part.split("–"))
                cited.update(range(a, b + 1))
            elif part:
                cited.add(int(part))
    first_cite = []
    for m in re.finditer(r"\[(\d[\d,–]*)\]", body):
        for part in m.group(1).split(","):
            if not part:
                continue
            a, _, b = part.partition("–")
            for n in range(int(a), int(b or a) + 1):
                if n not in first_cite:
                    first_cite.append(n)
    if n_refs > MAX_REFS:
        problems.append(f"{n_refs} references (maximum {MAX_REFS})")
    if cited != set(range(1, n_refs + 1)):
        problems.append(f"cited {sorted(cited)} vs listed 1..{n_refs}")
    if first_cite != sorted(first_cite):
        problems.append("references are not numbered in order of first citation")
    # ---------------------------------------------------------------- figures and tables
    if re.search(r"Appendix|Table [A-Z]\d|Supplementary (Table|Figure) ", txt):
        problems.append("appendix or supplementary display item referenced")
    n_fig = len([p for p in paras if re.match(r"Figure \d+\. ", p)])
    n_tab = len([p for p in paras if re.match(r"Table \d+\. ", p)])
    for kind, n in (("Figure", n_fig), ("Table", n_tab)):
        caps, firsts = [], []
        for i in range(1, n + 1):
            lab = f"{kind} {i}"
            capre = re.compile(re.escape(lab) + r"\. ")
            cap = next((j for j, p in enumerate(paras) if capre.match(p)), None)
            pat = re.compile(re.escape(lab) + r"(?![0-9])")
            first = next((j for j, p in enumerate(paras) if pat.search(p) and not capre.match(p)), None)
            if first is None or cap is None or first > cap:
                problems.append(f"{lab} not cited before its caption (first {first}, caption {cap})")
            caps.append(cap if cap is not None else -1)
            firsts.append(first if first is not None else -1)
        if caps != sorted(caps) or firsts != sorted(firsts):
            problems.append(f"{kind.lower()}s not numbered in order of placement and first citation")
    # ---------------------------------------------------------------- numbers
    checks = []
    G = json.load(open(os.path.join(ROOT, "results", "paper_numbers.json")))
    big = G["models"][-1]
    M = lambda N, m, a=None, b="All": next(r for r in N["methods"] if r["method"] == m and r["bench"] == b and r["alpha"] == a)
    for meth, a in ((f"CORAL|{big}", 0.1), (f"Direct+conf|{big}", 0.1), (f"Direct|{big}", None)):
        r = M(G, meth, a)
        checks += [(f"general {meth} FA", pct(r["fa"], 1)), (f"general {meth} mutation", fx(r["mut_score"]))]
    bfile = os.path.join(ROOT, "results", "paper_numbers_biomed.json")
    if os.path.exists(bfile):
        Bn = json.load(open(bfile))
        bb = Bn["models"][-1]
        for meth, a in ((f"CORAL|{bb}", 0.1), (f"Direct+conf|{bb}", 0.1), (f"Direct|{bb}", None), ("CORAL-hetero", 0.1)):
            r = M(Bn, meth, a)
            checks += [(f"biomed {meth} FA", pct(r["fa"], 1)), (f"biomed {meth} domain", pct(r["det_real"])), (f"biomed {meth} mutation", fx(r["mut_score"]))]
        for r in Bn["crc"]:
            if r["bench"] == "All" and r["method"] in (f"CORAL|{m}" for m in Bn["models"]):
                checks.append((f"biomed {r['method']} CRC α={r['alpha']}", f"{fx(r['fa_mean'], 3)} ± {fx(r['fa_sd'], 3)}"))
    found = sum(s in txt for _, s in checks)
    for lab, s in checks:
        if s not in txt:
            problems.append(f"number not found: {lab} {s}")
    # ---------------------------------------------------------------- abstract and pending markers
    i = paras.index("Abstract")
    abstract = " ".join(p for p in paras[i + 1:i + 9] if p.startswith(("Background/Objectives:", "Methods:", "Results:", "Conclusions:")))
    n_words = len([w for w in abstract.split() if any(c.isalnum() for c in w)])
    n_pending = txt.count("⟦PENDING⟧")
    if final and n_pending:
        problems.append(f"{n_pending} PENDING markers left (run the biomedical suite first)")
    if os.path.exists(os.path.join(ROOT, "SMOKE_TEST_COPY")):
        problems.append("smoke-test copy: synthetic stand-in data, not results")
    print(f"{os.path.relpath(path, ROOT)}: {n_refs} references (max {MAX_REFS}), {len(cited)} cited; {n_fig} figures, {n_tab} tables; "
          f"key numbers {found}/{len(checks)}; abstract {n_words} words; PENDING markers: {n_pending}")
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
