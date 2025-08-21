#!/usr/bin/env bash
# /workspace/scripts/start_automation.sh

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$project_root"

echo "[+] Loading .env"
set -a
[ -f .env ] && source .env || true
set +a

if ! command -v docker >/dev/null 2>&1; then
  echo "[!] Docker is required. Install Docker then re-run." >&2
  exit 1
fi

echo "[+] Bringing up stack (traefik, redis, content-api, bot-api, workers, n8n)"
docker compose up -d

echo "[+] Waiting for n8n to be ready at ${N8N_PUBLIC_URL:-http://localhost:7056}"
for i in $(seq 1 60); do
  if curl -fsS "${N8N_PUBLIC_URL:-http://localhost:7056}/api/v1/workflows" >/dev/null 2>&1; then
    echo "[+] n8n API is responding"
    break
  fi
  sleep 2
done

if ! curl -fsS "${N8N_PUBLIC_URL:-http://localhost:7056}/api/v1/workflows" >/dev/null 2>&1; then
  echo "[!] n8n API is not reachable. Check N8N_PUBLIC_URL/WEBHOOK_URL in .env and reverse proxy." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "[i] jq not found; skipping auto-import. Use scripts/setup-n8n-api.sh later."
  exit 0
fi

if [[ -z "${N8N_KEY:-}" ]]; then
  echo "[i] N8N_KEY not set. Create an API key in n8n UI (Settings → API Keys) and export N8N_KEY then run scripts/setup-n8n-api.sh deploy"
  exit 0
fi

echo "[+] Deploying workflows via API"
"$project_root/scripts/n8n-manager.sh" deploy || true

echo "[✓] Stack started. Ensure workflows are active and have Cron triggers for automation."
