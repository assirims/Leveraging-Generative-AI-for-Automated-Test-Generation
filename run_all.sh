#!/bin/bash
# Full pipeline. Step 04 (generative models) takes about 11 hours on two CPU cores; it resumes from results/llm/*.jsonl,
# so every later step can be re-run from the stored model outputs without the models.
set -e
cd "$(dirname "$0")"
mkdir -p results/logs
python3 01_verify_raw.py
python3 02_build_data.py
python3 02b_build_biomed.py
python3 04_generate.py qwen0.5b all   > results/logs/04_generate_qwen0.5b.log 2>&1   # development model
python3 04_generate.py llama3b impl   > results/logs/04_generate_llama3b.log 2>&1    # LLM-made faulty programs
python3 04_generate.py qwen3b all     > results/logs/04_generate_qwen3b.log 2>&1     # evaluation model
python3 05_execute.py 2               > results/logs/05_execute.log 2>&1
python3 06_analysis.py                > results/logs/06_analysis.log 2>&1
python3 dev_select_design.py          > results/logs/dev_select_design.log 2>&1
python3 06c_high_probability.py       > results/logs/06c_high_probability.log 2>&1
python3 06d_worked_example.py         > results/logs/06d_worked_example.log 2>&1
python3 07_figures.py
python3 09_make_diagram.py
python3 08_collect_results.py
python3 tests/test_crc.py
python3 tests/test_execution.py
python3 tests/test_ltt.py
(cd manuscript && node build_manuscript.js)
python3 10_verify_manuscript.py
node manuscript_biomed/build_biomedicines.js
python3 tests/test_biomed_benchmark.py
python3 10b_verify_biomedicines.py
