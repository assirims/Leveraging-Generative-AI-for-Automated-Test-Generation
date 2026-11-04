@echo off
REM Full pipeline (Windows). Step 04 takes about 11 hours on two CPU cores and resumes from results\llm\*.jsonl.
REM Note: the execution sandbox uses POSIX resource limits; on Windows run steps 05 onwards in WSL or a Linux container.
cd /d "%~dp0"
if not exist results\logs mkdir results\logs
python 01_verify_raw.py || exit /b 1
python 02_build_data.py || exit /b 1
python 02b_build_biomed.py || exit /b 1
python 04_generate.py qwen0.5b all > results\logs\04_generate_qwen0.5b.log 2>&1 || exit /b 1
python 04_generate.py llama3b impl > results\logs\04_generate_llama3b.log 2>&1 || exit /b 1
python 04_generate.py qwen3b all > results\logs\04_generate_qwen3b.log 2>&1 || exit /b 1
python 05_execute.py 2 > results\logs\05_execute.log 2>&1 || exit /b 1
python 06_analysis.py > results\logs\06_analysis.log 2>&1 || exit /b 1
python dev_select_design.py > results\logs\dev_select_design.log 2>&1 || exit /b 1
python 06c_high_probability.py > results\logs\06c_high_probability.log 2>&1 || exit /b 1
python 06d_worked_example.py > results\logs\06d_worked_example.log 2>&1 || exit /b 1
python 07_figures.py || exit /b 1
python 09_make_diagram.py || exit /b 1
python 08_collect_results.py || exit /b 1
python tests\test_crc.py || exit /b 1
python tests\test_execution.py || exit /b 1
python tests\test_ltt.py || exit /b 1
cd manuscript && node build_manuscript.js && cd ..
python 10_verify_manuscript.py
node manuscript_biomed\build_biomedicines.js || exit /b 1
python tests\test_biomed_benchmark.py || exit /b 1
python 10b_verify_biomedicines.py
