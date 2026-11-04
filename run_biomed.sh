#!/bin/bash
# Biomedical suite (BioMedFn) - main study of the Biomedicines manuscript. Linux, macOS or WSL.
#   ./run_biomed.sh                 generate with the models (needs llama.cpp and the model files), then everything else
#   ./run_biomed.sh --skip-models   use the model logs results/llm/*_biomed.jsonl that are already there
set -e
cd "$(dirname "$0")"
export CORAL_SUITE=biomed
mkdir -p results/logs
python3 02b_build_biomed.py
if [ "$1" != "--skip-models" ]; then
  python3 04_generate.py qwen0.5b all > results/logs/04_generate_qwen0.5b_biomed.log 2>&1
  python3 04_generate.py llama3b impl > results/logs/04_generate_llama3b_biomed.log 2>&1
  python3 04_generate.py qwen3b all   > results/logs/04_generate_qwen3b_biomed.log 2>&1
fi
python3 05_execute.py 2              > results/logs/05_execute_biomed.log 2>&1
python3 06_analysis.py               > results/logs/06_analysis_biomed.log 2>&1
python3 06c_high_probability.py      > results/logs/06c_high_probability_biomed.log 2>&1
python3 06d_worked_example.py        > results/logs/06d_worked_example_biomed.log 2>&1
python3 06e_biomed_faults.py         > results/logs/06e_biomed_faults.log 2>&1
python3 07_figures.py
python3 08_collect_results.py
python3 tests/test_biomed_benchmark.py
node manuscript_biomed/build_biomedicines.js
python3 10b_verify_biomedicines.py --final
