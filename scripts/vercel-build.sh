#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[vercel-build] Install & build dashboard..."
cd "$ROOT/dashboard"
npm ci
npm run build

echo "[vercel-build] Copy built assets to public/..."
cd "$ROOT"
rm -rf public
mkdir -p public
cp -r dashboard/dist/. public/

echo "[vercel-build] Done."

#!/usr/bin/env bash
# Build Vite dashboard into public/ for Vercel static CDN + same-origin /api routes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/dashboard"
npm ci
npm run build
cd "$ROOT"
rm -rf public
mkdir -p public
cp -r dashboard/dist/. public/
