#!/usr/bin/env bash
# Renderiza uma rota do app num Chrome real em resolução de monitor e salva PNG.
# Uso: ./shot.sh [rota] [largura] [altura]   ex.: ./shot.sh / 1920 1080
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
ROUTE="${1:-/}"; W="${2:-1920}"; H="${3:-1080}"
OUT="$(pwd)/.shot/shot.png"
mkdir -p "$(pwd)/.shot"; rm -f "$OUT"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --user-data-dir="$(mktemp -d)" --no-first-run --no-default-browser-check \
  --window-size="$W,$H" --screenshot="$OUT" \
  "http://127.0.0.1:5005${ROUTE}" >/dev/null 2>&1
echo "$OUT"
