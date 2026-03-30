#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[vercel-build] Install & build dashboard..."
cd "$ROOT/dashboard"
npm ci
npm run build

echo "[vercel-build] Copy built assets to public/..."
cd "$ROOT"
rm -rf api/static
mkdir -p api/static
cp -r dashboard/dist/. api/static/

echo "[vercel-build] (Optional) also copy to public/ for static CDN..."
rm -rf public
mkdir -p public
cp -r dashboard/dist/. public/

echo "[vercel-build] Done."
