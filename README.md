# Leveraging generative AI for automated test generation in biomedical and clinical software

Replication package for the manuscript *Leveraging Generative AI for Automated Test Generation in Biomedical and
Clinical Software: N-Version Oracles with Distribution-Free False-Alarm Guarantees*, prepared for *Biomedicines*
(MDPI), Special Issue "Artificial Intelligence in Biomedical Engineering and Precision Medicine".

CORAL (Calibrated ORacle Admission for LLM-generated tests) lets a small open-weight LLM write unit tests from a
function's specification and bounds the probability that the generated suite fails on a correct program. Everything
runs on an ordinary computer without a GPU: the models are 4-bit GGUF files served by llama.cpp on a CPU (general suite: two cloud cores; biomedical suite: a laptop CPU with eight threads).

## Status of the results

| Part | Status |
|---|---|
| General-code development suite (HumanEval + QuixBugs, 195 problems) | complete: model outputs, executions, results |
| BioMedFn benchmark (112 biomedical functions, faults, developer tests) | complete (model-free) |
| Biomedical evaluation (models on BioMedFn) | complete: model outputs, executions, results, manuscript |

The biomedical model outputs (`results/llm/{qwen0.5b,llama3b,qwen3b}_biomed.jsonl`) were generated on 2 November
2026 on a laptop (Intel Core Ultra 9 185H, 64 GB RAM, Windows 11 Pro; llama.cpp release b12054, CPU build, 8 threads;
all three model files verified by SHA-256). Run logs: `results/logs/pc_*` and `results/logs/*_biomed.log`. Every
logged response replays exactly with this code (`CORAL_SUITE=biomed CORAL_REPLAY_ONLY=1 python 04_generate.py <model>`),
so the analysis is reproducible without the models: `./run_biomed.sh --skip-models` re-creates all biomedical tables,
figures and the manuscript, and `10b_verify_biomedicines.py --final` checks it (30 references, display items, key
numbers, no PENDING marker). The pipeline was also smoke-tested with synthetic stand-ins (`tools/smoke_fake_llm.py`,
scratch copy only); no synthetic number is part of the package or the manuscript.

## Method in one paragraph

An open-weight LLM reads only the specification (signature and docstring) of a function. It writes test assertions
`f(x) == y` and, independently, K = 5 implementations of the function (one greedy, four sampled). The implementations
are executed on every input and vote on the expected value, together with the test writer's prediction, which carries
weight w = 2K times its token probability. The weighted support share of the winning value is the oracle score.
Conformal risk control picks the smallest score threshold such that a suite fails on a correct program with
probability at most α (in expectation over calibration sets); Learn-then-Test (fixed-sequence binomial tests) makes the
bound hold with probability at least 1 - δ. Only assertions above the threshold are run on the program under test.

## Two suites, one code base

| Suite | `CORAL_SUITE` | Problems | Role |
|---|---|---|---|
| general | `general` (default) | HumanEval (164) + QuixBugs (31) | development, design selection on Qwen2.5-0.5B, calibration source for the transfer experiment |
| biomed | `biomed` | BioMedFn (112) | held-out biomedical evaluation (main study) |

Every suite reads and writes its own files (`problems[_biomed].jsonl`, `executions[_biomed].jsonl`,
`results/tables[/biomed]`, `results/figures[/biomed]`, `results/llm/<model>[_biomed].jsonl`,
`results/paper_numbers[_biomed].json`), so running one suite never changes the other.

## BioMedFn

`data/raw/biomedfn/{clinical,dosing,omics,biosignal}.py` define 112 functions in four domains (clinical scores and
decision support; renal function and precision dosing; genomics and multi-omics; physiological signals and
wearables): specification with formula, units, rounding and error conditions, the published source of the formula,
the reference body, one seeded domain fault (six categories: unit or scale, coefficient or constant, threshold or
boundary, formula or estimator, logic or indexing, missing step or safeguard) and the developer test inputs.
`02b_build_biomed.py` builds `data/processed/problems_biomed.jsonl` (worked examples and expected outputs computed from
the reference), checks that every fault compiles, differs from the reference and is detected by a developer test, and
writes the catalogue `results/tables/biomed/biomed_benchmark_catalog.csv` and `data/raw/biomedfn/MANIFEST.json`.
The functions were written for this study from the cited formulas with the assistance of a generative AI tool and
checked by the build script; see the manuscript's Acknowledgments.

## Folder layout

| Path | Content |
|---|---|
| `00_PAPER/` | Biomedicines manuscript (Word and PDF), cover letter, submission checklist, run instructions, `Figures/` |
| `01_verify_raw.py` ... `10b_verify_biomedicines.py` | Pipeline (see below) |
| `config.py` | Paths per suite, models, seeds and all fixed parameters |
| `lib/` | llama.cpp client with replay logs, sandboxed execution, assertion parser, mutation operators, committee oracles |
| `tests/` | Tests of conformal risk control, Learn-then-Test, execution sandbox and the BioMedFn benchmark |
| `tools/smoke_fake_llm.py` | Smoke test only: synthetic stand-ins for model logs (refuses to run outside a scratch copy) |
| `data/raw/` | HumanEval and QuixBugs at fixed commits, BioMedFn sources, `MANIFEST.json` files with SHA-256 |
| `data/processed/` | Problems, executions (general: `executions.jsonl.gz`), per-split results; `biomed/` for the biomedical suite |
| `results/llm/` | Every prompt and response with token probabilities (also the replay cache) |
| `results/tables/`, `results/figures/` | General suite; `biomed/` subfolders for the biomedical suite |
| `manuscript_biomed/` | Builder of the Biomedicines manuscript (Node.js + docx); every number is read from the result files |
| `manuscript/` | Builder of the earlier general-code version of the manuscript (kept for reproducibility; also holds `refs.js`) |

## Reproduce

General suite (complete; model outputs included, so no model is needed):

```
python 01_verify_raw.py --skip-models
./run_all.sh            # or run_all.bat; step 04 replays results/llm/*.jsonl if the models are absent (CORAL_REPLAY_ONLY=1)
```

Biomedical suite:

```
# 1) model step (Windows): set LLAMA_SERVER=C:\path\to\llama-server.exe  then  RUN_MODELS_BIOMED.bat
#    or (Linux/WSL): python3 01_verify_raw.py --download-models && export LLAMA_SERVER=/path/to/llama-server && ./run_biomed.sh
# 2) everything after the models (Linux/WSL; the sandbox uses POSIX resource limits):
./run_biomed.sh --skip-models
```

The model step is deterministic (greedy decoding and fixed seeds) and resumable. On two CPU cores the general suite
took about 11 hours. The biomedical suite (112 problems) took 23 min (Qwen2.5-0.5B), 22 min (Llama-3.2-3B,
one implementation per function) and 1 h 42 min (Qwen2.5-3B) on eight threads of a laptop CPU.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1 | `01_verify_raw.py [--fetch] [--download-models]` | raw data and model files verified against SHA-256 |
| 2 | `02_build_data.py`, `02b_build_biomed.py` | `problems.jsonl` (195), `problems_biomed.jsonl` (112) |
| 4 | `04_generate.py <model> [tests\|impl\|all]` | assertions and committee implementations; logs in `results/llm/` |
| 5 | `05_execute.py [workers]` | all programs on all inputs, coverage, checks |
| 6 | `06_analysis.py` | methods, 500 random splits, shift/transfer, cross-fitting, paired tests, bootstrap |
| 6b | `dev_select_design.py` | design selection on the development model (general suite only) |
| 6c | `06c_high_probability.py` | Learn-then-Test versus conformal risk control |
| 6d | `06d_worked_example.py` | worked example |
| 6e | `06e_biomed_faults.py` | detection by fault category and domain (biomedical suite) |
| 7, 9 | `07_figures.py`, `09_make_diagram.py` | figures |
| 8 | `08_collect_results.py` | `results/paper_numbers[_biomed].json` |
| 10 | `node manuscript_biomed/build_biomedicines.js`, `10b_verify_biomedicines.py [--final]` | manuscript and its checks |

## Data and models

* HumanEval (Chen et al., 2021), github.com/openai/human-eval, commit 6d43fb9 (MIT).
* QuixBugs (Lin et al., 2017), github.com/jkoppel/QuixBugs, commit 4257f44 (MIT).
* BioMedFn: created for this study (this package).
* Qwen2.5-0.5B-Instruct and Qwen2.5-3B-Instruct (GGUF Q4_K_M, Qwen) and Llama-3.2-3B-Instruct (GGUF Q4_K_M,
  bartowski; Llama 3.2 Community License, Built with Llama). URLs at pinned revisions and SHA-256 in
  `data/raw/MANIFEST.json`; `01_verify_raw.py --download-models` fetches them.

## Requirements

Python 3.11+ with numpy, pandas, scipy, matplotlib, python-docx (`requirements.txt`); llama.cpp (`llama-server`, set
`LLAMA_SERVER`) for the model step; Graphviz (`dot`) for Figure 1; Node.js 18+ with the `docx` package for the
manuscript; LibreOffice (optional) for the PDF.

## Safety

Generated code runs in separate isolated Python processes (`python -I`) with a 1.5 GB memory limit, 0.5 s per call and
30 s per program, and with standard output suppressed.

Generative AI (Claude, Anthropic) assisted with code, the BioMedFn functions and text; see the manuscript.
