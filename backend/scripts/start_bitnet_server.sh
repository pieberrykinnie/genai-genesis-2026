#!/usr/bin/env bash
set -euo pipefail

# Starts BitNet llama-server with safe local defaults.
# Required env:
#   BITNET_HOME: path to cloned microsoft/BitNet repo
#   BITNET_MODEL_PATH: path to GGUF model file
# Optional env:
#   HOST (default 127.0.0.1)
#   PORT (default 8080)
#   CTX_SIZE (default 4096)
#   THREADS (default half cores, min 2)
#   N_PREDICT (default 1024)
#   TEMPERATURE (default 0.3)

BITNET_HOME="${BITNET_HOME:-}"
BITNET_MODEL_PATH="${BITNET_MODEL_PATH:-${MODEL_PATH:-}}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-4096}"
N_PREDICT="${N_PREDICT:-1024}"
TEMPERATURE="${TEMPERATURE:-0.3}"

if [[ -z "$BITNET_HOME" ]]; then
  echo "ERROR: BITNET_HOME is required (path to microsoft/BitNet clone)." >&2
  exit 1
fi

if [[ -z "$BITNET_MODEL_PATH" ]]; then
  echo "ERROR: BITNET_MODEL_PATH is required (path to GGUF model)." >&2
  exit 1
fi

if [[ ! -d "$BITNET_HOME" ]]; then
  echo "ERROR: BITNET_HOME does not exist: $BITNET_HOME" >&2
  exit 1
fi

if [[ ! -f "$BITNET_MODEL_PATH" ]]; then
  echo "ERROR: model file not found: $BITNET_MODEL_PATH" >&2
  exit 1
fi

if [[ -z "${THREADS:-}" ]]; then
  cores="$(nproc)"
  THREADS="$(( cores / 2 ))"
  if [[ "$THREADS" -lt 2 ]]; then
    THREADS=2
  fi
fi

cd "$BITNET_HOME"

if [[ ! -x "build/bin/llama-server" && ! -x "build/bin/Release/llama-server" ]]; then
  echo "ERROR: llama-server binary not found. Build BitNet first (see README build steps)." >&2
  exit 1
fi

echo "Starting BitNet llama-server"
echo "  model: $BITNET_MODEL_PATH"
echo "  host: $HOST"
echo "  port: $PORT"
echo "  ctx:  $CTX_SIZE"
echo "  threads: $THREADS"

# BitNet's script wraps llama.cpp server and expects the build output in build/bin.
exec python3 run_inference_server.py \
  --model "$BITNET_MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$CTX_SIZE" \
  --threads "$THREADS" \
  --n-predict "$N_PREDICT" \
  --temperature "$TEMPERATURE"
