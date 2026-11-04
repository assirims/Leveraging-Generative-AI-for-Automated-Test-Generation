"""Step 07 - Figures 2-7 (300 dpi PNG; Fig. 1 is drawn by 09_make_diagram.py). Colour encodes the method (fixed order, colour-blind-checked palette);
markers and direct labels carry the same information in print."""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ALPHAS, FIGS, LLM_LABEL, PROC_OUT, SUITE, TABLES, TEST_MODELS  # noqa: E402

BIO = SUITE == "biomed"
# output file of each figure; general suite: names carry the numbers of the earlier general-code manuscript
OUT = ({"reliability": "Fig2_oracle_reliability.png", "tradeoff": "Fig5_tradeoff.png", "validity": "Fig4_validity.png",
        "detection": "Fig3_detection.png", "ksize": "Fig7_committee_size.png", "hp": "Fig6_high_probability.png"}
       if not BIO else {k: f"biomed_{k}.png" for k in ("reliability", "tradeoff", "validity", "detection", "ksize", "hp", "domains", "benchmark")})

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
STYLE = {  # method -> (colour, marker, label)
    "CORAL": ("#2a78d6", "^", "CORAL (committee + direct vote)"),
    "CORAL (committee only)": ("#1baf7a", "v", "CORAL, committee only"),
    "Direct+conf": ("#eb6834", "o", "Direct + token confidence"),
    "CORAL-hetero": ("#4a3aa7", "D", "CORAL, pooled committee (both models)"),
    "CORAL (no amplification)": ("#eda100", "s", "CORAL, no amplification"),
    "Direct": ("#eb6834", "o", "Direct (all assertions)"),
    "N-version vote": ("#1baf7a", "s", "N-version majority vote"),
    "Doctest": ("#eda100", "P", "Spec examples (doctest)"),
    "Developer tests": ("#52514e", "*", "Developer tests"),
}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "legend.frameon": False,
                     "savefig.dpi": 300, "savefig.bbox": "tight"})


def models_present():
    m = pd.read_csv(os.path.join(TABLES, "methods_summary.csv"))
    return [x for x in TEST_MODELS if any(m.method.str.endswith("|" + x))]


def fig2_reliability(models):
    R = pd.read_csv(os.path.join(TABLES, "oracle_reliability.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, meth, title in ((axes[0], "CORAL", "(a) Execution-vote agreement"), (axes[1], "Direct+conf", "(b) Token probability of the expected value")):
        ax.plot([0, 1], [0, 1], ls="--", color=INK2, lw=0.8)
        for j, m in enumerate(models):
            g = R[(R.method == meth) & (R.model == m) & (R.n >= 5)].sort_values("score_mean")
            col = ["#eda100", "#eb6834", "#2a78d6"][j % 3]
            mk = ["s", "o", "^"][j % 3]
            ax.plot(g.score_mean, g.accuracy, color=col, marker=mk, ms=4.5, lw=1.4, label=LLM_LABEL[m])
        ax.set_title(title, fontsize=9, loc="left")
        ax.set_xlabel("Oracle score (agreement share)" if meth == "CORAL" else "Minimum token probability")
        ax.set_xlim(0, 1.02)
        ax.set_ylim(0, 1.02)
    axes[0].set_ylabel("Share of correct expected values")
    axes[0].legend(loc="upper left", fontsize=7.5)
    fig.savefig(os.path.join(FIGS, OUT["reliability"]))
    plt.close(fig)


def fig3_tradeoff(models):
    W = pd.read_csv(os.path.join(TABLES, "threshold_sweep.csv"))
    M = pd.read_csv(os.path.join(TABLES, "methods_summary.csv"))
    M = M[(M.bench == "All")]
    fig, axes = plt.subplots(1, len(models), figsize=(7.4, 2.9), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, m in zip(axes, models):
        for meth in ("Direct+conf", "CORAL (committee only)", "CORAL"):
            g = W[W.method == f"{meth}|{m}"].copy()
            g["det"] = g[["det_real", "det_llm"]].mean(axis=1)
            g = g.sort_values("fa")
            c, mk, lab = STYLE[meth]
            ax.plot(g.fa, g.mut_score, color=c, lw=1.5, label=lab)
        for meth in ("Direct", "N-version vote"):
            r = M[(M.method == f"{meth}|{m}") & M.alpha.isna()]
            if len(r):
                c, mk, lab = STYLE[meth]
                ax.scatter(r.fa, r.mut_score, color="white", edgecolor=c, marker=mk, s=38, zorder=5, linewidths=1.4, label=lab)
        for a in (0.05, 0.1):
            ax.axvline(a, color=GRID, lw=1.0, zorder=0)
        ax.set_title(LLM_LABEL[m], fontsize=9, loc="left")
        ax.set_xlabel("False-alarm rate on correct programs")
        ax.set_xlim(-0.01, None)
    axes[0].set_ylabel("Mutation score (killable mutants)")
    h, l = axes[0].get_legend_handles_labels()
    fig.subplots_adjust(bottom=0.33, wspace=0.08)
    fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0), fontsize=7.5)
    fig.savefig(os.path.join(FIGS, OUT["tradeoff"]))
    plt.close(fig)


def fig4_validity(models):
    A = pd.read_csv(os.path.join(TABLES, "crc_splits_summary.csv"))
    S = pd.read_csv(os.path.join(TABLES, "crc_transfer_general.csv" if BIO else "crc_shift_quixbugs.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, (title, D, col) in zip(axes, (("(a) Random calibration/test halves", A[A.bench == "All"], "fa_mean"),
                                          ("(b) Calibrate on general code, test on BioMedFn" if BIO else "(b) Calibrate on HumanEval, test on QuixBugs", S, "fa"))):
        ax.plot([0, 0.22], [0, 0.22], ls="--", color=INK2, lw=0.8)
        for j, m in enumerate(models):
            for meth in ("Direct+conf", "CORAL"):
                g = D[D.method == f"{meth}|{m}"].sort_values("alpha")
                c, mk, lab = STYLE[meth]
                ax.plot(g.alpha + (j - 1) * 0.004, g[col], color=c, marker=["s", "o", "^"][j % 3], ms=4.5, lw=1.0,
                        alpha=0.55 + 0.15 * j)
        ax.set_title(title, fontsize=8.5, loc="left")
        ax.set_xlabel("Tolerated false-alarm probability α")
        ax.set_xticks(list(ALPHAS))
        ax.set_xlim(0, 0.23)
    axes[0].set_ylabel("Realised false-alarm rate")
    hs = [Line2D([0], [0], color=STYLE[m][0], lw=1.4, label=STYLE[m][2]) for m in ("CORAL", "Direct+conf")]
    hs += [Line2D([0], [0], color=INK2, marker=["s", "o", "^"][j % 3], lw=0, label=LLM_LABEL[m]) for j, m in enumerate(models)]
    fig.subplots_adjust(bottom=0.27, wspace=0.08)
    fig.legend(handles=hs, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0), fontsize=7.5)
    fig.savefig(os.path.join(FIGS, OUT["validity"]))
    plt.close(fig)


def fig5_detection(models):
    M = pd.read_csv(os.path.join(TABLES, "methods_summary.csv"))
    M = M[M.bench == "All"]
    rows = [("Developer tests", "Developer tests", None), ("Doctest", "Doctest", None)]
    for m in models:
        rows += [(f"Direct|{m}", "Direct", None), (f"Direct+conf|{m}", "Direct+conf", 0.1), (f"CORAL|{m}", "CORAL", 0.1)]
    rows += [("CORAL-hetero", "CORAL-hetero", 0.1)]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 3.4), sharey=True)
    for ax, (col, title) in zip(axes, (("det_real", "(a) Seeded domain faults" if BIO else "(a) Real faults (QuixBugs)"), ("det_llm", "(b) LLM-made faults"), ("mut_score", "(c) Mutants"))):
        labels, vals, colors = [], [], []
        for meth, fam, a in rows:
            r = M[(M.method == meth) & ((M.alpha.isna()) if a is None else (M.alpha == a))]
            if not len(r):
                continue
            model = meth.split("|")[1] if "|" in meth else ""
            show = {"CORAL-hetero": "Pooled committee (CORAL)", "Doctest": "Spec examples", "Direct+conf": "Direct + confidence"}.get(fam, fam)
            labels.append((LLM_LABEL.get(model, "") + " " + show).strip() if model else show)
            vals.append(float(r[col].iloc[0]))
            colors.append(STYLE[fam][0])
        y = np.arange(len(labels))[::-1]
        ax.barh(y, vals, color=colors, height=0.62)
        for yy, v in zip(y, vals):
            if not np.isnan(v):
                ax.text(v + 0.01, yy, f"{v:.2f}", va="center", fontsize=6.5, color=INK2)
        ax.set_title(title, fontsize=8.5, loc="left")
        ax.set_xlim(0, 1.12)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=7)
        ax.grid(axis="y", visible=False)
    axes[1].set_xlabel("Share of faulty programs detected (CORAL and Direct + confidence at α = 0.10; cross-fitted)")
    fig.savefig(os.path.join(FIGS, OUT["detection"]))
    plt.close(fig)


def fig6_ablation(models):
    A = pd.read_csv(os.path.join(TABLES, "crc_splits_summary.csv"))
    A = A[(A.bench == "All") & (A.alpha == 0.1)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for j, m in enumerate(models):
        col = ["#eda100", "#eb6834", "#2a78d6"][j % 3]
        mk = ["s", "o", "^"][j % 3]
        ks = [k for k in range(1, 6) if len(A[A.method == f"CORAL K={k}|{m}"])]
        axes[0].plot(ks, [float(A[A.method == f"CORAL K={k}|{m}"].mut_score.iloc[0]) for k in ks], color=col, marker=mk, lw=1.4, label=LLM_LABEL[m])
        axes[1].plot(ks, [float(A[A.method == f"CORAL K={k}|{m}"].asserts.iloc[0]) for k in ks], color=col, marker=mk, lw=1.4, label=LLM_LABEL[m])
    axes[0].set_ylabel("Mutation score at α = 0.10")
    axes[1].set_ylabel("Admitted assertions per problem")
    for ax, t in zip(axes, ("(a) Fault detection", "(b) Size of the admitted suite")):
        ax.set_xlabel("Committee size K (implementations)")
        ax.set_xticks(range(1, 6))
        ax.set_title(t, fontsize=8.5, loc="left")
    axes[0].legend(fontsize=7.5)
    fig.savefig(os.path.join(FIGS, OUT["ksize"]))
    plt.close(fig)


def fig7_high_probability(models):
    """Expectation (CRC) versus high-probability (LTT) control on the same random splits (06c_high_probability.py)."""
    S = pd.read_csv(os.path.join(PROC_OUT, "hp_splits.csv"))
    big = models[-1]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    pos, data, cols = [], [], []
    for i, a in enumerate(ALPHAS):
        for j, proc in enumerate(("CRC", "LTT")):
            g = S[(S.method == f"CORAL|{big}") & (S.alpha == a) & (S.procedure == proc)]
            pos.append(i * 3 + j)
            data.append(g.fa.values)
            cols.append("#2a78d6" if proc == "CRC" else "#4a3aa7")
        ax.hlines(a, i * 3 - 0.45, i * 3 + 1.45, colors=INK, linestyles="--", lw=0.9, zorder=4)
    bp = ax.boxplot(data, positions=pos, widths=0.7, patch_artist=True, whis=(5, 95), showfliers=False,
                    medianprops={"color": "white", "lw": 1.4})
    for patch, c in zip(bp["boxes"], cols):
        patch.set_facecolor(c)
        patch.set_edgecolor(c)
    for k, c in zip(range(len(bp["whiskers"])), [c for c in cols for _ in (0, 1)]):
        bp["whiskers"][k].set_color(c)
        bp["caps"][k].set_color(c)
    ax.set_xticks([i * 3 + 0.5 for i in range(len(ALPHAS))])
    ax.set_xticklabels([f"α = {a:.2f}" for a in ALPHAS])
    ax.set_ylabel("Realised false-alarm rate (test half)")
    ax.set_title(f"(a) {LLM_LABEL[big]}, CORAL: spread over splits", fontsize=8.5, loc="left")
    ax.grid(axis="x", visible=False)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#2a78d6", label="CRC (mean ≤ α)"),
                       plt.Rectangle((0, 0), 1, 1, color="#4a3aa7", label="LTT (≤ α w.p. ≥ 0.9)"),
                       Line2D([0], [0], color=INK, ls="--", lw=0.9, label="α")], fontsize=7, loc="upper left")
    ax = axes[1]
    for meth in ("CORAL", "Direct+conf"):
        c, mk, lab = STYLE[meth]
        for proc, ls in (("CRC", "-"), ("LTT", "--")):
            g = S[(S.method == f"{meth}|{big}") & (S.procedure == proc)].groupby("alpha").mut_score.mean()
            ax.plot(g.index, g.values, color=c, marker=mk, ls=ls, ms=4.5, lw=1.4,
                    label=f"{'CORAL' if meth == 'CORAL' else 'Token confidence'}, {proc}")
    ax.set_xticks(list(ALPHAS))
    ax.set_xlabel("Tolerated false-alarm probability α")
    ax.set_ylabel("Mutation score (mean over splits)")
    ax.set_title("(b) Cost of the stronger guarantee", fontsize=8.5, loc="left")
    ax.legend(fontsize=7, loc="lower right")
    fig.subplots_adjust(wspace=0.3)
    fig.savefig(os.path.join(FIGS, OUT["hp"]))
    plt.close(fig)


DOMAIN_LABEL = {"clinical": "Clinical scores", "dosing": "Renal function\nand dosing", "omics": "Genomics and\nmulti-omics",
                "biosignal": "Signals and\nwearables"}
CAT_ORDER = ["threshold or boundary", "formula or estimator", "missing step or safeguard", "coefficient or constant",
             "unit or scale", "logic or indexing"]
CAT_COL = ["#2a78d6", "#1baf7a", "#eda100", "#eb6834", "#4a3aa7", "#8a8984"]


def fig_benchmark():
    """BioMedFn composition: problems per domain, split by the category of the seeded domain fault (model-free)."""
    C = pd.read_csv(os.path.join(TABLES, "biomed_benchmark_catalog.csv"))
    doms = ["clinical", "dosing", "omics", "biosignal"]
    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    left = np.zeros(len(doms))
    for cat, col in zip(CAT_ORDER, CAT_COL):
        v = np.array([int(((C.domain == d) & (C.fault_category == cat)).sum()) for d in doms])
        ax.barh(range(len(doms)), v, left=left, color=col, height=0.62, label=cat, edgecolor="white", linewidth=1.0)
        for y, (l0, x) in enumerate(zip(left, v)):
            if x >= 2:
                ax.text(l0 + x / 2, y, str(x), ha="center", va="center", fontsize=7, color="white")
        left += v
    for y, tot in enumerate(left):
        ax.text(tot + 0.4, y, f"{int(tot)}", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(range(len(doms)))
    ax.set_yticklabels([DOMAIN_LABEL[d].replace("\n", " ") for d in doms], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("Problems (colour: category of the seeded domain fault)")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(left) + 3)
    ax.set_axisbelow(True)
    fig.subplots_adjust(bottom=0.36)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.32), ncol=3, fontsize=7)
    fig.savefig(os.path.join(FIGS, OUT["benchmark"]))
    plt.close(fig)


def fig_domains(models):
    """Detection per biomedical domain at alpha = 0.10 (cross-fitted thresholds) for the evaluation model."""
    M = pd.read_csv(os.path.join(TABLES, "methods_summary.csv"))
    big = models[-1]
    doms = ["clinical", "dosing", "omics", "biosignal"]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.8), sharey=True)
    meths = [(f"Direct+conf|{big}", "Direct+conf"), (f"CORAL|{big}", "CORAL"), ("CORAL-hetero", "CORAL-hetero")]
    for ax, (col, title) in zip(axes, (("det_real", "(a) Seeded domain faults"), ("det_llm", "(b) LLM-made faults"), ("mut_score", "(c) Mutants"))):
        w = 0.26
        for j, (meth, fam) in enumerate(meths):
            vals = []
            for d in doms:
                r = M[(M.method == meth) & (M.bench == d) & (M.alpha == 0.1)]
                vals.append(float(r[col].iloc[0]) if len(r) else np.nan)
            ax.bar(np.arange(len(doms)) + (j - 1) * w, vals, width=w - 0.03, color=STYLE[fam][0],
                   label={"Direct+conf": "Direct + token confidence", "CORAL": "CORAL", "CORAL-hetero": "CORAL, pooled committee"}[fam])
        ax.set_xticks(range(len(doms)))
        ax.set_xticklabels(["Clinical", "Dosing", "Omics", "Signals"], fontsize=7)
        ax.set_title(title, fontsize=8.5, loc="left")
        ax.set_ylim(0, 1.05)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Share detected (α = 0.10)")
    h, l = axes[0].get_legend_handles_labels()
    fig.subplots_adjust(bottom=0.3, wspace=0.08)
    fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0), fontsize=7.5)
    fig.savefig(os.path.join(FIGS, OUT["domains"]))
    plt.close(fig)


def main():
    if BIO:
        plt.rcParams["axes.axisbelow"] = True     # grid behind bars (biomedical figures)
        fig_benchmark()
    if not os.path.exists(os.path.join(TABLES, "methods_summary.csv")):
        print("no results yet for", SUITE, "- only the benchmark figure was drawn")
        return
    models = models_present()
    fig2_reliability(models)
    fig3_tradeoff(models)
    fig4_validity(models)
    fig5_detection(models)
    fig6_ablation(models)
    if os.path.exists(os.path.join(PROC_OUT, "hp_splits.csv")):
        fig7_high_probability(models)
    if BIO:
        fig_domains(models)
    print("figures written for", models)


if __name__ == "__main__":
    main()
