#!/bin/bash
# Runs all generation steps sequentially on two CPU cores (Qwen2.5-0.5B about 1.5 h, Llama-3.2-3B about 2 h,
# Qwen2.5-3B about 7.5 h). Each step resumes from its JSONL log, so the chain can be restarted at any time.
cd "$(dirname "$0")"
python3 04_generate.py qwen0.5b all > results/logs/04_generate_qwen0.5b.log 2>&1
python3 04_generate.py llama3b impl > results/logs/04_generate_llama3b.log 2>&1
python3 04_generate.py qwen3b all > results/logs/04_generate_qwen3b.log 2>&1
date > results/logs/gen_chain.done
