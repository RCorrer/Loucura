#!/usr/bin/env bash
set -e
SRC="shared-ui/src"
APPS=("segmenthub" "engagementhub" "clientview360" "compasshub")
for app in "${APPS[@]}"; do
  DEST="$app/frontend/src/shared-ui"
  echo "Sincronizando -> $DEST"
  rm -rf "$DEST"
  mkdir -p "$DEST"
  cp -r "$SRC/." "$DEST/"
done
echo "Sync concluído. Rode 'npm run build' nos apps alterados."
