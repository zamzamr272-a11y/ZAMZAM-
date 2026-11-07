#!/usr/bin/env bash
set -euo pipefail

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/nexora-postgres-$STAMP.dump.enc"

read -r -s -p "Passphrase enkripsi backup: " NEXORA_BACKUP_PASSPHRASE
printf '\n'
if [[ ${#NEXORA_BACKUP_PASSPHRASE} -lt 16 ]]; then
  echo "Gunakan passphrase minimal 16 karakter." >&2
  exit 1
fi
export NEXORA_BACKUP_PASSPHRASE

TMP="$OUT.tmp"
trap 'rm -f "$TMP"; unset NEXORA_BACKUP_PASSPHRASE' EXIT

docker compose exec -T db pg_dump -U nexora -d nexora -Fc \
  | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
      -pass env:NEXORA_BACKUP_PASSPHRASE -out "$TMP"
mv "$TMP" "$OUT"
chmod 600 "$OUT"

echo "Encrypted PostgreSQL backup created: $OUT"
echo "Back up the private upload volume separately; this file contains PostgreSQL only."
