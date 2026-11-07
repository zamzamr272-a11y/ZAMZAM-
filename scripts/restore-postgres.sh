#!/usr/bin/env bash
set -euo pipefail

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "Usage: $0 path/to/nexora-postgres-YYYYMMDDTHHMMSSZ.dump.enc" >&2
  exit 2
fi

read -r -p "Restore akan mengganti objek database NEXORA yang ada. Ketik RESTORE untuk lanjut: " CONFIRM
[[ "$CONFIRM" == "RESTORE" ]] || { echo "Restore dibatalkan."; exit 1; }
read -r -s -p "Passphrase backup: " NEXORA_BACKUP_PASSPHRASE
printf '\n'
export NEXORA_BACKUP_PASSPHRASE

restart_api() { docker compose start api >/dev/null 2>&1 || true; }
trap 'restart_api; unset NEXORA_BACKUP_PASSPHRASE' EXIT

docker compose stop api
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -pass env:NEXORA_BACKUP_PASSPHRASE -in "$BACKUP_FILE" \
  | docker compose exec -T db pg_restore --clean --if-exists --no-owner --no-acl -U nexora -d nexora

docker compose start api
trap - EXIT
unset NEXORA_BACKUP_PASSPHRASE
echo "Restore command completed. Check API logs and run application smoke tests."
