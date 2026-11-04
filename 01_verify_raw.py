"""Step 1 - obtain and verify the raw data.

The benchmarks are taken from their public GitHub repositories at fixed commits:
  HumanEval  github.com/openai/human-eval      commit 6d43fb980f9fee3c892a914eda09951f772ad10d  (data/HumanEval.jsonl.gz, MIT)
  QuixBugs   github.com/jkoppel/QuixBugs       commit 4257f44b0ff1181dedaedee6a447e133219fcebf  (Python programs and JSON tests, MIT)
`python 01_verify_raw.py --fetch` clones them (needs git and network); `python 01_verify_raw.py` (default) writes or
checks data/raw/MANIFEST.json with the SHA-256 of every raw file used and of the model files;
`python 01_verify_raw.py --download-models` downloads the three model files (about 4.4 GB) from Hugging Face at the
pinned revisions into models/ and verifies their SHA-256.
"""
import hashlib
import json
import os
import subprocess
import sys

from config import LLMS, RAW, ROOT, TEST_MODELS

REPOS = {"human-eval": ("https://github.com/openai/human-eval.git", "6d43fb980f9fee3c892a914eda09951f772ad10d"),
         "QuixBugs": ("https://github.com/jkoppel/QuixBugs.git", "4257f44b0ff1181dedaedee6a447e133219fcebf")}
MODEL_SRC = {
    "qwen0.5b": ("https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_k_m.gguf",
                 "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"),
    "qwen1.5b": ("https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf",
                 "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"),
    "qwen3b": ("https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/7dabda4d13d513e3e842b20f0d435c732f172cbe/qwen2.5-3b-instruct-q4_k_m.gguf",
               "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d"),
    "llama3b": ("https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/5ab33fa94d1d04e903623ae72c95d1696f09f9e8/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
                "6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff"),
}


USED_MODELS = TEST_MODELS + ["llama3b"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def used_files():
    files = [os.path.join("human-eval", "data", "HumanEval.jsonl.gz"), os.path.join("human-eval", "LICENSE"), os.path.join("QuixBugs", "LICENSE")]
    tdir = os.path.join(RAW, "QuixBugs", "json_testcases")
    for fn in sorted(os.listdir(tdir)):
        n = fn[:-5]
        files += [os.path.join("QuixBugs", "json_testcases", fn), os.path.join("QuixBugs", "python_programs", n + ".py"),
                  os.path.join("QuixBugs", "correct_python_programs", n + ".py")]
    return files


def download_models():
    import urllib.request
    for m in USED_MODELS:
        path = LLMS[m]
        url, h = MODEL_SRC[m]
        if os.path.exists(path) and sha(path) == h:
            print("present and verified:", os.path.relpath(path, ROOT))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("downloading", url, flush=True)
        tmp = path + ".part"
        with urllib.request.urlopen(url) as r, open(tmp, "wb") as out:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            for chunk in iter(lambda: r.read(1 << 22), b""):
                out.write(chunk)
                got += len(chunk)
                if total:
                    print(f"  {got / total:.0%}", end="\r", flush=True)
        if sha(tmp) != h:
            os.remove(tmp)
            raise SystemExit(f"SHA-256 mismatch for {url}")
        os.replace(tmp, path)
        print("  verified", os.path.relpath(path, ROOT))


def main():
    if "--download-models" in sys.argv:
        download_models()
    if "--fetch" in sys.argv:
        for name, (url, commit) in REPOS.items():
            dst = os.path.join(RAW, name)
            if not os.path.exists(dst):
                subprocess.run(["git", "clone", "-q", url, dst], check=True)
            subprocess.run(["git", "-C", dst, "checkout", "-q", commit], check=True)
    man_f = os.path.join(RAW, "MANIFEST.json")
    data = {f: sha(os.path.join(RAW, f)) for f in used_files()}
    models = {}
    for m in USED_MODELS:   # only the models used in the study
        path = LLMS[m]
        url, h = MODEL_SRC[m]
        rel = os.path.relpath(path, ROOT)
        ok = os.path.exists(path) and ("--skip-models" in sys.argv or sha(path) == h)
        models[rel] = {"url": url, "sha256": h, "present_and_verified": bool(ok) if "--skip-models" not in sys.argv else "not checked"}
    man = {"repositories": {k: {"url": u, "commit": c} for k, (u, c) in REPOS.items()}, "data_files": data, "models": models}
    if os.path.exists(man_f) and "--write" not in sys.argv:
        old = json.load(open(man_f))
        bad = [f for f, h in old["data_files"].items() if data.get(f) != h]
        print(f"{len(data)} data files, {len(bad)} mismatches; models verified: {sum(v['present_and_verified'] is True for v in models.values())}/{len(models)}")
        if bad:
            print("MISMATCH:", bad[:10])
            sys.exit(1)
    else:
        json.dump(man, open(man_f, "w"), indent=1)
        print(f"wrote {man_f}: {len(data)} data files; models verified: {sum(v['present_and_verified'] is True for v in models.values())}/{len(models)}")


if __name__ == "__main__":
    main()
