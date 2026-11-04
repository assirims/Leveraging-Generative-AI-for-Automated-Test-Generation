"""Step 4 - query the generative models.

For every problem and every test-writing model (Qwen2.5-0.5B/1.5B/3B):
  (a) one greedy call that writes N_ASSERT assertions `assert f(...) == expected` from the specification only,
      with per-token probabilities (used for the direct-oracle baseline and its confidence score);
  (b) K_IMPL implementations of the function written from the specification only (1 greedy + 4 sampled);
      they form the N-version committee whose executions vote on the expected outputs.
For Llama-3.2-3B only one greedy implementation is generated; incorrect ones serve as realistic (LLM-made) faults.
Usage: python 04_generate.py <model> [tests|impl|all]   (suite from CORAL_SUITE: general | biomed)
"""
import json
import os
import sys
import time

from config import K_IMPL, LLM_LABEL, LLMS, LOGS, N_ASSERT, PROBLEMS_FILE, PROC, SUFFIX, SUITE, TEMP, llm_log
from lib import llm

SYS_TEST = "You are an expert software tester."
SYS_IMPL = "You are an expert Python programmer."
STOP_IMPL = ("```", "\nif __name__", "\nprint(", "\nassert ", "\n# Test", "\n# Example", "\n# test", "\n# example")


def test_messages(p):
    return [{"role": "system", "content": SYS_TEST},
            {"role": "user", "content":
             f"Write {N_ASSERT} unit-test assertions for the Python function `{p['entry']}` specified below. The assertions must "
             "check the behaviour required by the specification, not the behaviour of any particular implementation. "
             "Cover typical cases, edge cases and boundary values.\n"
             f"Write one assertion per line in the form `assert {p['entry']}(<arguments>) == <expected result>`, using only "
             "literal values. Do not write anything else.\n\n```python\n" + p["spec"] + "```"}]


def impl_messages(p):
    return [{"role": "system", "content": SYS_IMPL},
            {"role": "user", "content": "Implement the following Python function according to its specification. "
             "Return the complete function.\n\n```python\n" + p["spec"] + "```"}]


def impl_prefill(p):
    """The assistant turn starts with the specification and the body indentation, so the model writes only the body."""
    spec = p["spec"] if p["spec"].endswith("\n") else p["spec"] + "\n"
    return "```python\n" + spec + "    "


def main():
    model = sys.argv[1]
    what = sys.argv[2] if len(sys.argv) > 2 else "all"
    probs = [json.loads(l) for l in open(PROBLEMS_FILE)]
    log_file = llm_log(model)
    n_rep = llm.load_replay(log_file)
    print(f"{LLM_LABEL[model]} [{SUITE}]: {len(probs)} problems, {n_rep} logged responses; "
          f"LLM_THREADS={os.environ.get('LLM_THREADS', '2')}; platform={sys.platform}", flush=True)
    proc = None
    if os.environ.get("CORAL_REPLAY_ONLY") != "1":
        proc = llm.start_server(LLMS[model], os.path.join(LOGS, f"llama_server_{model}{SUFFIX}.log"))
        mp = llm.model_path()
        assert mp in ("", os.path.basename(LLMS[model])), f"server runs a different model: {mp}"
    t0, out = time.time(), []
    try:
        for i, p in enumerate(probs):
            rec = {"pid": p["pid"], "model": model}
            if what in ("tests", "all") and model != "llama3b":
                r = llm.complete(test_messages(p), "```python\n", f"test:{p['pid']}", log_file, max_tokens=400, n_probs=1)
                rec["tests"] = r
            if what in ("impl", "all"):
                ks = range(1) if model == "llama3b" else range(K_IMPL)
                rec["impls"] = []
                for k in ks:
                    r = llm.complete(impl_messages(p), impl_prefill(p), f"impl:{p['pid']}:{k}", log_file,
                                     max_tokens=320, temperature=0.0 if k == 0 else TEMP, seed=2026 + k, stop=STOP_IMPL)
                    rec["impls"].append(r)
            out.append(rec)
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(probs)}  {time.time() - t0:.0f}s", flush=True)
    finally:
        llm.stop_server(proc)
    with open(os.path.join(PROC, f"gen_{model}{SUFFIX}.jsonl"), "w") as fh:
        for rec in out:
            fh.write(json.dumps(rec) + "\n")
    print(f"done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
