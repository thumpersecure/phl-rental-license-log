#!/usr/bin/env bash
# Archive a CLOSED month: gzip changes/YYYY-MM*.ndjson, keep the .ots proofs untouched
# (they commit to the uncompressed bytes), record the uncompressed SHA-256 in
# changes/SHA256SUMS. Usage: scripts/archive_month.sh 2026-11
# Refuses the current UTC month and any month whose proof hash does not match its file.
set -euo pipefail
M="${1:?usage: archive_month.sh YYYY-MM}"
cd "$(dirname "$0")/../changes"
[ "$M" \< "$(date -u +%Y-%m)" ] || { echo "refusing: $M is not a closed month"; exit 1; }
for f in "$M".ndjson "$M"-*.ndjson; do
  [ -f "$f" ] || continue
  sum=$(sha256sum "$f" | cut -d' ' -f1)
  proof=$(ots info "$f.ots" | awk '/sha256 hash/{print $NF}')
  [ "$sum" = "$proof" ] || { echo "refusing: $f does not match $f.ots"; exit 1; }
  gzip -9 -n -k "$f"
  [ "$(gunzip -c "$f.gz" | sha256sum | cut -d' ' -f1)" = "$sum" ] || { rm -f "$f.gz"; echo "round-trip failed: $f"; exit 1; }
  echo "$sum  $f" >> SHA256SUMS
  rm "$f"
  echo "archived $f.gz"
done
