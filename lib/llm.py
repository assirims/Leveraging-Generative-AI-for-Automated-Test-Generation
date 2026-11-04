"""Client for a local llama.cpp server (llama-server) running a 4-bit open-weight instruction-tuned model.

Prompts are rendered with the model's own chat template (/apply-template) and the assistant turn is pre-filled
(e.g. with the specification), so that the model continues the code instead of repeating it. Greedy decoding uses
temperature 0; sampled implementations use temperature 0.8, top-p 0.95 and a fixed seed per sample.
Every request and response (with per-token probabilities where requested) is appended to a JSONL log, and a run
can be resumed or replayed from that log without the model.
"""
import json
import os
import subprocess
import time
import urllib.request

LLAMA_SERVER = os.environ.get("LLAMA_SERVER", "/home/claude/tools/llama.cpp/build/bin/llama-server")
PORT = int(os.environ.get("LLM_PORT", "8091"))
URL = f"http://127.0.0.1:{PORT}"


def _post(path, payload, timeout=1800):
    req = urllib.request.Request(URL + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def healthy():
    try:
        with urllib.request.urlopen(URL + "/health", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def start_server(model, log_path, ctx=4096, threads=None):
    threads = threads or int(os.environ.get("LLM_THREADS", "2"))   # CPU threads (2 for the general suite)
    if healthy():
        raise RuntimeError(f"a server is already running on port {PORT}")
    base = [LLAMA_SERVER, "-m", model, "-c", str(ctx), "-t", str(threads), "-tb", str(threads), "--port", str(PORT),
            "--host", "127.0.0.1", "-np", "1", "--seed", "2026"]
    # optional flags of recent llama.cpp builds (no web UI, small prompt cache); retried without them if refused
    for cmd in (base + ["--no-webui", "--cache-ram", "256"], base):
        log = open(log_path, "a")
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(300):
            if proc.poll() is not None:
                break
            if healthy():
                return proc
            time.sleep(1)
        if proc.poll() is None:
            proc.terminate()
            raise RuntimeError("llama-server did not start")
    raise RuntimeError("llama-server exited; see " + log_path)


def stop_server(proc):
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=30)
    except Exception:
        proc.kill()


_MODEL = {}


def model_path():
    if "p" in _MODEL:
        return _MODEL["p"]
    try:
        with urllib.request.urlopen(URL + "/props", timeout=10) as r:
            _MODEL["p"] = os.path.basename(json.loads(r.read().decode()).get("model_path", ""))
            return _MODEL["p"]
    except Exception:
        return ""


def render(messages):
    return _post("/apply-template", {"messages": messages})["prompt"]


_REPLAY = {}


def load_replay(log_file):
    _REPLAY.clear()
    if os.path.exists(log_file):
        for line in open(log_file, encoding="utf-8"):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            _REPLAY[d["key"]] = d
    return len(_REPLAY)


def complete(messages, prefill, tag, log_file, max_tokens=320, temperature=0.0, seed=2026, stop=("```",), n_probs=0):
    """Generate the continuation of `prefill` in the assistant turn. Returns dict(text, seconds, tokens, probs)."""
    key = json.dumps([tag, messages, prefill, max_tokens, temperature, seed, list(stop), n_probs], sort_keys=True)
    if key in _REPLAY:
        d = _REPLAY[key]
        return {"text": d["text"], "seconds": d["seconds"], "tokens": d["tokens"], "probs": d.get("probs"), "replay": True}
    prompt = render(messages) + prefill
    payload = {"prompt": prompt, "n_predict": max_tokens, "temperature": temperature, "top_p": 0.95 if temperature > 0 else 1.0,
               "top_k": 0 if temperature > 0 else 1, "min_p": 0.0, "seed": seed, "stop": list(stop), "cache_prompt": True}
    if n_probs:
        payload["n_probs"] = n_probs
    t0 = time.time()
    r = _post("/completion", payload)
    dt = round(time.time() - t0, 3)
    probs = None
    if n_probs:
        probs = [[c.get("token"), c.get("logprob", c.get("prob"))] for c in r.get("completion_probabilities", [])]
    out = {"text": r["content"], "seconds": dt, "tokens": r.get("tokens_predicted"), "probs": probs}
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"key": key, "tag": tag, "messages": messages, "prefill": prefill, "max_tokens": max_tokens,
                             "temperature": temperature, "seed": seed, "stop": list(stop), "n_probs": n_probs,
                             "text": out["text"], "seconds": dt, "tokens": out["tokens"], "probs": probs,
                             "model": model_path()}, ensure_ascii=False) + "\n")
    return out
