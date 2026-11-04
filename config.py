"""Shared paths and settings for the CORAL replication package (calibrated oracle admission for LLM-generated tests)."""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")
RESULTS = os.path.join(ROOT, "results")
LOGS = os.path.join(RESULTS, "logs")
LLM_LOGS = os.path.join(RESULTS, "llm")
MODELS = os.path.join(ROOT, "models")

# Two problem suites share all code and settings:
#   general  HumanEval + QuixBugs (195 problems): development of the method and design selection
#   biomed   BioMedFn (biomedical and clinical functions): held-out biomedical evaluation (main study)
# Select with the environment variable CORAL_SUITE (default: general). Every suite reads and writes its own files,
# so that running one suite never changes the inputs or results of the other.
SUITE = os.environ.get("CORAL_SUITE", "general")
assert SUITE in ("general", "biomed"), "CORAL_SUITE must be 'general' or 'biomed'"
SUFFIX = "" if SUITE == "general" else "_" + SUITE
PROBLEMS_FILE = os.path.join(PROC, f"problems{SUFFIX}.jsonl")
PROC_OUT = PROC if SUITE == "general" else os.path.join(PROC, SUITE)       # per-suite processed outputs
TABLES = os.path.join(RESULTS, "tables") if SUITE == "general" else os.path.join(RESULTS, "tables", SUITE)
FIGS = os.path.join(RESULTS, "figures") if SUITE == "general" else os.path.join(RESULTS, "figures", SUITE)
GROUPS = ["HumanEval", "QuixBugs"] if SUITE == "general" else ["clinical", "dosing", "omics", "biosignal"]
for _d in (PROC, PROC_OUT, TABLES, FIGS, LOGS, LLM_LOGS):
    os.makedirs(_d, exist_ok=True)


def llm_log(model):
    """JSONL log (and replay cache) of every prompt and response of a model for the current suite."""
    return os.path.join(LLM_LOGS, f"{model}{SUFFIX}.jsonl")

SEED = 2026
N_SPLITS = int(os.environ.get("CORAL_SPLITS", "500"))   # random calibration/test splits of problems
N_BOOT = 2000
DEV_SPLITS = 200      # random splits used to select the score design on the development model (dev_select_design.py)
ALPHAS = (0.05, 0.10, 0.20)                               # tolerated false-alarm probability per correct program

# Generative models (4-bit GGUF, llama.cpp). The three Qwen2.5 models write tests and spec-derived implementations;
# Llama-3.2-3B only writes one (greedy) implementation per problem, which serves as an external source of realistic faults.
LLMS = {
    "qwen0.5b": os.path.join(MODELS, "qwen2.5-0.5b-instruct-gguf", "qwen2.5-0.5b-instruct-q4_k_m.gguf"),
    "qwen1.5b": os.path.join(MODELS, "qwen2.5-1.5b-instruct-gguf", "qwen2.5-1.5b-instruct-q4_k_m.gguf"),
    "qwen3b": os.path.join(MODELS, "qwen2.5-3b-instruct-gguf", "qwen2.5-3b-instruct-q4_k_m.gguf"),
    "llama3b": os.path.join(MODELS, "llama-3.2-3b-instruct-gguf", "Llama-3.2-3B-Instruct-Q4_K_M.gguf"),
}
LLM_LABEL = {"qwen0.5b": "Qwen2.5-0.5B", "qwen1.5b": "Qwen2.5-1.5B", "qwen3b": "Qwen2.5-3B", "llama3b": "Llama-3.2-3B"}
TEST_MODELS = ["qwen0.5b", "qwen3b"]   # development model, evaluation model
K_IMPL = 5                  # spec-derived implementations per problem and model (1 greedy + 4 sampled)
TEMP = 0.8                  # sampling temperature for the 4 sampled implementations
N_ASSERT = 8                # assertions requested from the model per problem
N_AMPLIFY = 24              # extra inputs per problem obtained by type-aware mutation of the model's inputs
CALL_TIMEOUT = 0.5          # seconds per function call
MAX_MUTANTS = 40            # mutants per reference program (random sample if more)
N_SELFMUT = 20              # mutants of the development model's greedy implementation (design selection only)
W_DIRECT = 2.0              # weight of the direct-prediction vote relative to the committee size (w = 2K; selected in dev_select_design.py, Table 5 of the manuscript)


def read_executions(suite=None):
    """All execution records of a suite (data/processed/executions[_biomed].jsonl, or its gzip copy)."""
    import gzip
    import json
    sfx = SUFFIX if suite is None else ("" if suite == "general" else "_" + suite)
    p = os.path.join(PROC, f"executions{sfx}.jsonl")
    fh = open(p) if os.path.exists(p) else gzip.open(p + ".gz", "rt")
    with fh:
        return [json.loads(line) for line in fh]
