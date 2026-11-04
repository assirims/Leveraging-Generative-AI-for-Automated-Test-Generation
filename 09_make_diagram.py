"""Step 09 - Fig. 1: the CORAL framework (Graphviz)."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import FIGS  # noqa: E402

DOT = r'''digraph G {
  graph [rankdir=TB, fontname="DejaVu Sans", fontsize=11, nodesep=0.35, ranksep=0.35, pad=0.2, bgcolor="white", newrank=true];
  node  [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=10, color="#52514e", penwidth=0.8, margin="0.12,0.07"];
  edge  [color="#52514e", arrowsize=0.7, penwidth=0.9, fontname="DejaVu Sans", fontsize=8, fontcolor="#52514e"];

  spec [label="Specification\n(signature + docstring)", fillcolor="#f4f3ef"];
  put  [label="Program under test\n(may be faulty)", fillcolor="#f4f3ef"];
  tests [label="1  Test writer (open-weight LLM)\nassertions f(x) == y\n(inputs + direct oracles)", fillcolor="#dbe9fa"];
  impls [label="1  N-version committee (same LLM)\nK implementations\nwritten from the spec only", fillcolor="#dbe9fa"];
  amp  [label="Input amplification (optional)\ntype-aware mutation\n(no model calls)", fillcolor="#ffffff", style="rounded,filled,dashed"];
  vote [label="2  Weighted execution vote\nplurality output = oracle\nscore = weighted support share", fillcolor="#d5f0e5"];
  cal  [label="3  Calibration\nproblems with known-correct\nreference programs", fillcolor="#fde3d6"];
  crc  [label="Conformal risk control\nthreshold t with\nP(false alarm) ≤ α", fillcolor="#d5f0e5"];
  suite [label="4  Admitted test suite\nassertions with score ≥ t", shape=box, style="rounded,filled,bold", fillcolor="#ffffff"];
  out  [label="Run on program under test\nfailure = bug report\n(false-alarm rate ≤ α)", fillcolor="#ffffff"];

  {rank=same; crc; put;}
  {rank=same; vote; cal;}
  spec -> tests; spec -> impls;
  tests -> amp [label="inputs"];
  tests -> vote [label="inputs + predicted outputs\n(weight 2K × token confidence)"];
  amp -> vote [style=dashed]; impls -> vote [label="K votes"];
  vote -> crc; cal -> crc;
  crc -> suite; vote -> suite;
  suite -> out; put -> out;
  {rank=same; suite; out;}
}
'''


def main():
    src = os.path.join(FIGS, "Fig1_framework.dot")
    with open(src, "w") as fh:
        fh.write(DOT)
    subprocess.run(["dot", "-Tpng", "-Gdpi=300", src, "-o", os.path.join(FIGS, "Fig1_framework.png")], check=True)
    print("ok Fig1")


if __name__ == "__main__":
    main()
