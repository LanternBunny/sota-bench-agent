# AGENTS.md

## Setup And Mirrors
- Work from `/home/chengyuxuan/Agent/sota-bench-agent`; the expected runtime env is `conda activate langgraph`, then `pip install -r requirements.txt`.
- Force package mirrors in this repo: `start.sh` already exports Tsinghua pip mirror variables; for manual `pip install`, keep `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple` and `PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn` unless debugging mirror issues.
- Code reproduction is expected to force mirrors in `code_agent/executor.py`: pip uses `PIP_INDEX_URL`, Hugging Face uses `HF_ENDPOINT=https://hf-mirror.com`, Git clone uses `CODE_AGENT_GIT_SSL_BACKEND=gnutls`, and Conda package commands use `CODE_AGENT_CONDA_CHANNELS` with `--override-channels`.
- When creating Conda envs manually or in reproduction fixes, use Conda mirror channels with `--override-channels`; do not let reproduction depend on the default upstream channel.
- For LLaVA setup, clone/download `liuhaotian/llava-v1.5-7b` using the Hugging Face mirror when upstream HF is slow: `git -c http.sslBackend=gnutls clone https://hf-mirror.com/liuhaotian/llava-v1.5-7b`.
- This machine's Git may fail with `Unsupported SSL backend 'openssl'`; use per-command `git -c http.sslBackend=gnutls ...` instead of changing global Git config.
- Do not write Hugging Face tokens into repo files or shell history examples. If auth is required, rely on an already-set `HF_TOKEN`/`HUGGINGFACE_HUB_TOKEN` environment variable.
- `git-lfs` may be unavailable; if model `.bin`/`.model` files are tiny LFS pointers, use `HF_ENDPOINT=https://hf-mirror.com huggingface-cli download liuhaotian/llava-v1.5-7b --local-dir llava-v1.5-7b` after installing `huggingface_hub`.
- Hugging Face/Xet download timeouts should be retried rather than skipped; the executor sets `HF_HUB_DISABLE_XET=1`, longer hub timeouts, and retries retryable CAS/Xet/network failures.

## Main Entrypoints
- `streamlit run app.py` starts only the UI; `bash start.sh` starts both `langgraph dev` and Streamlit, kills old listeners on its configured ports, then writes LangGraph logs to `outputs/langgraph_dev.log`.
- `python graph.py "topic"` runs the research graph once with an in-memory checkpointer and writes reports under `outputs/reports/`.
- `python -m code_agent.run_reproduction --repo-url https://github.com/owner/repo --workspace-name name [--base-env langgraph]` is the standalone reproduction entrypoint used by the UI.
- LangGraph Studio reads `langgraph.json`; the graph names are `research_agent`, `search_agent`, `code_agent`, `query_planner`, `info_extractor`, `reflector`, and `report_writer`.

## Required Secrets And Env
- `.env` is loaded by `config.py` and `langgraph.json`; required keys are `SILICONFLOW_API_KEY`, `SILICONFLOW_BASE_URL`, and `TAVILY_API_KEY`; LangSmith keys are optional.
- Default models are `LLM_MODEL=deepseek-ai/DeepSeek-V3`, `FAST_MODEL=deepseek-ai/DeepSeek-V3`, and `JUDGE_MODEL=Qwen/Qwen2.5-72B-Instruct`.
- Reproduction timeouts are controlled by `CODE_AGENT_COMMAND_TIMEOUT` and `CODE_AGENT_GIT_CLONE_TIMEOUT`; `start.sh` raises them to `3600` and `1200` seconds.
- PyTorch CUDA wheel fallback is controlled by `CODE_AGENT_PYTORCH_WHEEL_INDEX`; default is `https://download.pytorch.org/whl/cu121`.
- Hugging Face retry behavior is controlled by `CODE_AGENT_HF_DOWNLOAD_RETRIES` and `CODE_AGENT_HF_DOWNLOAD_RETRY_DELAY`.

## Architecture Notes
- `graph.py` wires the research flow: query planner -> Tavily search -> paper filter -> info extraction or Best-of-N -> reflector -> PDF agent -> report writer -> experience buffer.
- `code_agent/graph.py` is a separate LangGraph loop: repo fetch -> parse -> execution plan -> Conda executor -> error analyzer -> patch generator, with `MAX_CODE_FIX_LOOPS=5` from `config.py`.
- `subgraphs/code_bridge.py` adapts the code agent into LangGraph Studio/UI state fields; standalone reproduction uses `code_agent/run_reproduction.py` instead.
- Search quality depends on Tavily plus GitHub URL normalization in `agents/search_agent.py`; code candidates are later filtered again by `_is_probable_code_repo`.

## Reproduction Gotchas
- Code reproduction clones GitHub repos into `outputs/repos/<workspace>/<repo>` with `--depth 1 --filter=blob:none`; reruns remove the existing repo directory first.
- The executor creates or reuses Conda envs named `sota_repo_<repo>`; it prefers requested `--base-env`, then `CODE_AGENT_BASE_ENV`, then current env, then `langgraph`.
- The execution planner must not emit `conda create`, `conda activate`, `conda deactivate`, or `conda init`; the executor owns environment creation and runs commands through `conda run`.
- The executor rewrites regular `pip install` commands to include the configured pip mirror, timeout, and retries; preserve that behavior when editing `code_agent/executor.py`.
- The executor preserves or injects PyTorch wheel indexes for `torch`/`torchvision`/`torchaudio` installs and rewrites Conda `pytorch-cuda` installs to pip wheels because mirrors often lack that package.
- The executor rewrites Hugging Face URLs from `https://huggingface.co/` to `HF_ENDPOINT` and rewrites `conda install/create/env create/env update` to the configured mirror channels.
- The error analyzer extracts local function source context for `python -c "from module import func"` failures; TypeError fixes should follow the actual signature instead of guessing parameters.
- Reproduction reports are written inside the cloned repo as `reproduction_report.md`; UI logs live under `outputs/reproduction_logs/`.
- `cleanup_conda_env(repo_dir)` exists but is not called by the graph, so failed reproduction envs can accumulate.

## Verification
- There is no test suite or lint config in the repo; use focused smoke checks instead.
- Quick import check: `python -m py_compile graph.py app.py code_agent/*.py agents/*.py subgraphs/*.py rl/*.py evaluation/*.py`.
- Research smoke test: `python graph.py "multimodal hallucination detection"` requires valid LLM and Tavily credentials.
- Reproduction smoke test: `python -m code_agent.run_reproduction --repo-url https://github.com/openai/openai-quickstart-python --workspace-name smoke --base-env langgraph`.
