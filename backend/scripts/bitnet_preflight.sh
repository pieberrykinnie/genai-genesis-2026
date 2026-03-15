#!/usr/bin/env bash
set -euo pipefail

# Verifies local host readiness for running BitNet on Linux CPU.

warn() {
  printf 'WARN: %s\n' "$*"
}

ok() {
  printf 'OK: %s\n' "$*"
}

need_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "found command: $cmd"
  else
    warn "missing command: $cmd"
  fi
}

check_python() {
  if command -v python3 >/dev/null 2>&1; then
    local v
    v="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    ok "python3 version detected: $v"
  else
    warn "python3 not found"
  fi
}

check_memory_disk() {
  local mem_gb
  local avail_gb
  mem_gb="$(awk '/MemTotal/ {printf "%.1f", $2/1024/1024}' /proc/meminfo)"
  avail_gb="$(df -BG . | awk 'NR==2 {gsub("G", "", $4); print $4}')"

  printf 'INFO: RAM total (GB): %s\n' "$mem_gb"
  printf 'INFO: Disk available in current filesystem (GB): %s\n' "$avail_gb"

  awk -v m="$mem_gb" 'BEGIN { if (m < 16) exit 1; else exit 0 }' || warn "<16 GB RAM may be insufficient for stable 8B local serving"
  if [[ "${avail_gb:-0}" -lt 20 ]]; then
    warn "<20 GB free disk in current filesystem may be tight for model artifacts"
  else
    ok "disk headroom check passed"
  fi
}

printf '== BitNet preflight (Linux CPU) ==\n'
need_cmd git
need_cmd cmake
need_cmd clang
need_cmd python3
need_cmd pip
need_cmd huggingface-cli
check_python
check_memory_disk

printf '\nNext step:\n'
printf '1) Clone BitNet: git clone --recursive https://github.com/microsoft/BitNet.git\n'
printf '2) Prepare model with setup_env.py\n'
printf '3) Launch server with scripts/start_bitnet_server.sh\n'
