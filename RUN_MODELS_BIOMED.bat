@echo off
REM Model step of the biomedical suite on Windows (the only step that needs the language models).
REM Before running: install Python 3.11+ ("pip install -r requirements.txt"), download a CPU build of llama.cpp
REM (github.com/ggml-org/llama.cpp/releases, file llama-<version>-bin-win-cpu-x64.zip), unzip it, and set
REM     set LLAMA_SERVER=C:\path\to\llama-server.exe
REM Takes several hours on a laptop CPU; it can be interrupted and restarted (finished calls are kept).
cd /d "%~dp0"
if "%LLAMA_SERVER%"=="" (
  echo Please set LLAMA_SERVER to the full path of llama-server.exe first.
  exit /b 1
)
if not exist results\logs mkdir results\logs
set CORAL_SUITE=biomed
python 01_verify_raw.py --download-models || exit /b 1
python 02b_build_biomed.py || exit /b 1
python 04_generate.py qwen0.5b all > results\logs\04_generate_qwen0.5b_biomed.log 2>&1 || exit /b 1
python 04_generate.py llama3b impl > results\logs\04_generate_llama3b_biomed.log 2>&1 || exit /b 1
python 04_generate.py qwen3b all > results\logs\04_generate_qwen3b_biomed.log 2>&1 || exit /b 1
echo.
echo Done. The model outputs are in results\llm\qwen0.5b_biomed.jsonl, qwen3b_biomed.jsonl and llama3b_biomed.jsonl.
echo Next: run "run_biomed.sh --skip-models" in WSL or Linux, or send these three files for the remaining steps.
