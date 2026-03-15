# ClearSite Backend

## Run

```bash
uv sync
uv run fastapi dev main.py
```

## Local BitNet Runtime Setup (Linux, CPU)

The backend already supports OpenAI-compatible local model servers.
This section adds a practical path to run
`HF1BitLLM/Llama3-8B-1.58-100B-tokens` via Microsoft BitNet.

### 1) Preflight checks

Run preflight to verify host tools and rough RAM/disk headroom:

```bash
./scripts/bitnet_preflight.sh
```

### 2) Build BitNet and prepare model

From a sibling directory (outside this backend project):

```bash
cd ..
git clone --recursive https://github.com/microsoft/BitNet.git
cd BitNet

# Optional but recommended: isolated env for BitNet toolchain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Prepare a low-RAM bring-up model first (0.7B)
python setup_env.py --hf-repo 1bitLLM/bitnet_b1_58-large --quant-type i2_s

# Optional on larger hosts: prepare the 8B model instead
# python setup_env.py --hf-repo HF1BitLLM/Llama3-8B-1.58-100B-tokens --quant-type i2_s
```

After setup completes, locate the generated GGUF model under `models/`.
Use the path in step 3.

### 3) Start local server (prototype)

Use helper wrapper from this backend repo:

```bash
BITNET_HOME=../BitNet \
BITNET_MODEL_PATH=../BitNet/models/bitnet_b1_58-large/ggml-model-i2_s.gguf \
./scripts/start_bitnet_server.sh
```

Defaults:
- Host: `127.0.0.1`
- Port: `8080`
- Context: `4096`
- Threads: half of CPU cores (minimum 2)

### 4) Connect backend to BitNet

Set `.env` values:

```bash
LLM_BACKEND=bitnet
BITNET_API_BASE=http://127.0.0.1:8080/v1
BITNET_MODEL=1bitLLM/bitnet_b1_58-large
BITNET_API_KEY=bitnet-local
```

Start backend:

```bash
uv run fastapi dev main.py
```

### 5) Validate runtime and integration

```bash
# Endpoint-level readiness
curl -s http://127.0.0.1:8080/v1/models | jq .

# App-level readiness
curl -s http://127.0.0.1:8000/health/llm | jq .

# Capability probe from this repository
uv run python scripts/probe_bitnet_server.py \
	--base-url http://127.0.0.1:8080/v1 \
	--model 1bitLLM/bitnet_b1_58-large
```

Expected:
- `models_reachable=True`
- `basic_chat_ok=True`
- `json_object_ok=True`

`json_schema` may fail on local llama.cpp-style servers; this is expected in current flow.

`huggingface-cli` does not need to be installed in the backend `uv` environment.
Install it in the BitNet runtime environment (or via `pipx`) since it is only needed for model download/setup.

## Environment Variables

```bash
ELECTRICITY_MAPS_API_KEY=
MAPTILER_API_KEY=
NOMINATIM_USER_AGENT=genai-genesis-2026-local-dev/1.0
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_API_BASE=https://api.groq.com/openai/v1
LLM_BACKEND=groq
LLM_TEMPERATURE=
LLM_PROVIDER=groq
BITNET_API_KEY=bitnet-local
BITNET_API_BASE=http://127.0.0.1:8080/v1
BITNET_MODEL=1bitLLM/bitnet_b1_58-large
MEMO_JOB_QUEUE_MAXSIZE=32
MEMO_JOB_WORKER_COUNT=1
MEMO_JOB_TIMEOUT_SECONDS=180
STRICT_DATA_MODE=true
STATCAN_CACHE_DIR=./data/statcan_cache
MODEL_PATH=./models/grid_strain_model.pkl
```

`LLM_BACKEND` currently supports `groq` and `bitnet`. Keep the BitNet server bound to localhost and point `BITNET_API_BASE` at its OpenAI-compatible `/v1` base URL.
Use `GET /health/llm` to check backend configuration and BitNet reachability.

BitNet llama.cpp servers typically support `response_format={"type":"json_object"}` but not `json_schema`; memo fallback coercion in validators remains the safety net.

Geocoding order is:

1. MapTiler geocoding API (if key works)
2. OpenStreetMap Nominatim fallback
3. Province centroid fallback only when `STRICT_DATA_MODE=false`

## Endpoints

- `GET /health`
- `GET /health/llm`
- `POST /api/assess`
- `POST /api/assess/stream` (SSE)
- `POST /api/memo-jobs`
- `GET /api/memo-jobs/{job_id}`
- `GET /api/memo-jobs/{job_id}/result`

## Async Memo Jobs

Submit a memo generation job with the same proposal payload shape used by `/api/assess`:

```bash
curl -s -X POST http://127.0.0.1:8000/api/memo-jobs \
	-H 'Content-Type: application/json' \
	-d '{"address":"Municipal District of Greenview, Grande Prairie, Alberta","province":"AB","it_load_mw":200,"pue":1.5,"wue":1.9,"cooling_type":"evaporative","facility_type":"hyperscale","capex_cad":5000,"construction_months":36,"has_onsite_generation":true,"renewable_ppa":false}'
```

Then poll status and fetch result:

```bash
curl -s http://127.0.0.1:8000/api/memo-jobs/<job_id> | jq .
curl -s http://127.0.0.1:8000/api/memo-jobs/<job_id>/result | jq .
```

When BitNet is unavailable, memo jobs degrade to deterministic fallback output and return `result.fallback_used=true`.

## Data + ML Scripts

- `uv run python scripts/download_data.py`
- `uv run python scripts/download_data.py --allow-errors` (optional; default exits non-zero on failures)
- `uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.zip --water-csv ./data/38-10-0250-01.zip`
- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl`
- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl --allow-synthetic` (explicit opt-in only)
- `uv run python scripts/evaluate_railtracks_workflow.py --skip-judge`
- `uv run python scripts/evaluate_railtracks_workflow.py` (requires Groq key for JudgeEvaluator)
- `uv run python scripts/probe_bitnet_server.py`
- `uv run python scripts/probe_bitnet_server.py --base-url http://127.0.0.1:8080/v1 --model 1bitLLM/bitnet_b1_58-large`

## Railtracks Viz (Windows)

Use UTF-8 console encoding to avoid emoji encoding crashes:

```bash
cmd /c "set PYTHONIOENCODING=utf-8 && uv run railtracks viz"
```

## IESO Playwright Downloader (for anti-bot pages)

If direct script download returns HTML interstitial pages for IESO files:

1. `uv sync`
2. `uv run playwright install chromium`
3. `uv run python scripts/download_ieso_playwright.py --start-year 2020 --end-year 2025 --out-dir ./data`

Then retrain:

- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl`

## Systemd Example (production hardening)

Create `/etc/systemd/system/bitnet-llama.service`:

```ini
[Unit]
Description=BitNet llama-server
After=network.target

[Service]
Type=simple
User=bitnet
Group=bitnet
WorkingDirectory=/opt/BitNet
Environment=MODEL_PATH=/opt/BitNet/models/HF1BitLLM-Llama3-8B-1.58-100B-tokens/ggml-model-i2_s.gguf
Environment=HOST=127.0.0.1
Environment=PORT=8080
Environment=CTX_SIZE=4096
Environment=THREADS=8
Environment=N_PREDICT=1024
Environment=TEMPERATURE=0.3
ExecStart=/opt/genai-genesis-2026/backend/scripts/start_bitnet_server.sh
Restart=on-failure
RestartSec=5
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bitnet-llama
sudo systemctl status bitnet-llama
```
