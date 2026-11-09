#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} != "--inside-npx" ]]; then
  export npm_config_fund=false npm_config_audit=false
  exec npx --yes --package=n8n@2.46.6 -- bash "$0" --inside-npx "${1:-artifacts/n8n}"
fi

out=$2
mkdir -p "$out"
sandbox=$(mktemp -d)
api_pid=
n8n_pid=
cleanup() {
  local status=$?
  if [[ -n "$n8n_pid" ]]; then kill "$n8n_pid" 2>/dev/null || true; fi
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
  wait "$n8n_pid" "$api_pid" 2>/dev/null || true
  if [[ "$status" != 0 ]]; then
    for log in "$sandbox"/{import,publish,n8n,api}.log; do
      if [[ -f "$log" ]]; then
        echo "Diagnostics from $(basename "$log")"
        tail -50 "$log" | sed -E 's/(signature=)[^[:space:]"&]+/\1[redacted]/g'
      fi
    done
  fi
  rm -rf -- "$sandbox"
}
trap cleanup EXIT

export N8N_USER_FOLDER="$sandbox"
export N8N_LISTEN_ADDRESS=127.0.0.1 N8N_HOST=127.0.0.1 N8N_PORT=5678
export WEBHOOK_URL=http://127.0.0.1:5678/
export N8N_DIAGNOSTICS_ENABLED=false N8N_VERSION_NOTIFICATIONS_ENABLED=false
export N8N_TEMPLATES_ENABLED=false N8N_RUNNERS_ENABLED=false
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true N8N_SSRF_PROTECTION_ENABLED=false

{
  printf 'n8n version '
  n8n --version
  printf 'Workflow logisticsTriage1\n'
  printf 'GitHub run %s, attempt %s, commit %s\n' \
    "${GITHUB_RUN_ID:-local}" "${GITHUB_RUN_ATTEMPT:-local}" "${GITHUB_SHA:-local}"
} > "$out/n8n-run.log"

n8n import:workflow --input=workflow/logistics-triage.json > "$sandbox/import.log" 2>&1
grep -F 'Successfully imported 1 workflow.' "$sandbox/import.log" >> "$out/n8n-run.log"
n8n publish:workflow --id=logisticsTriage1 > "$sandbox/publish.log" 2>&1
grep -F 'Publishing workflow with ID: logisticsTriage1' "$sandbox/publish.log" >> "$out/n8n-run.log"

python -m uvicorn logistics_lab.api:app --host 127.0.0.1 --port 8000 > "$sandbox/api.log" 2>&1 &
api_pid=$!
n8n start > "$sandbox/n8n.log" 2>&1 &
n8n_pid=$!

for url in http://127.0.0.1:8000/healthz http://127.0.0.1:5678/healthz/readiness; do
  for _ in {1..60}; do
    if curl --fail --silent --max-time 2 "$url" > /dev/null; then break; fi
    sleep 1
  done
  curl --fail --silent --show-error --max-time 3 "$url" > /dev/null
done

python scripts/n8n_probe.py | tee -a "$out/n8n-run.log"
