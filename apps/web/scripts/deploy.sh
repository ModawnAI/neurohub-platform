#!/usr/bin/env bash
# NeuroHub Web Deploy Script
# Deploys the web app to the self-hosted server at 103.22.220.93
# Usage: bash apps/web/scripts/deploy.sh
set -euo pipefail

SSH_KEY="/tmp/neurohub_key"
SSH_HOST="yookj@103.22.220.93"
SSH_PORT="3093"
SSH_OPTS="-i $SSH_KEY -p $SSH_PORT -o StrictHostKeyChecking=no"
REMOTE_WEB="/home/yookj/neurohub-platform/neurohub-repo/apps/web"
REMOTE_NODE="/home/yookj/neurohub-platform/local/micromamba/envs/nodejs/bin/node"
REMOTE_BUN="/home/yookj/neurohub-platform/local/micromamba/envs/nodejs/bin/bun"
LOCAL_WEB="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== 1/5 Syncing files ==="
rsync -avz --delete \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='.env.local' \
  "$LOCAL_WEB/" \
  -e "ssh $SSH_OPTS" \
  "$SSH_HOST:$REMOTE_WEB/"

echo "=== 2/5 Installing deps + building on server ==="
ssh $SSH_OPTS "$SSH_HOST" << REMOTE
  export PATH="\$(dirname $REMOTE_BUN):\$PATH"
  cd "$REMOTE_WEB"
  bun install
  rm -f .next/lock
  bun run build
REMOTE

echo "=== 3/5 Copying static assets to standalone ==="
ssh $SSH_OPTS "$SSH_HOST" << REMOTE
  cd "$REMOTE_WEB"
  # Copy static + public into standalone so all assets are self-contained
  mkdir -p .next/standalone/.next
  rm -rf .next/standalone/.next/static
  cp -r .next/static .next/standalone/.next/
  rm -rf .next/standalone/public
  cp -r public .next/standalone/
REMOTE

echo "=== 4/5 Restarting server ==="
ssh $SSH_OPTS "$SSH_HOST" << REMOTE
  # Kill old server
  fuser -k 3000/tcp 2>/dev/null || true
  sleep 1
  # Start new server with full node path
  cd "$REMOTE_WEB/.next/standalone"
  PORT=3000 nohup $REMOTE_NODE server.js > /tmp/nextjs.log 2>&1 &
  sleep 2
REMOTE

echo "=== 5/5 Verifying ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://103.22.220.93:3093")
if [ "$HTTP_CODE" = "200" ]; then
  echo "Deploy successful! HTTP $HTTP_CODE"
  # Verify a static asset too
  BUILD_ID=$(ssh $SSH_OPTS "$SSH_HOST" "cat $REMOTE_WEB/.next/standalone/.next/BUILD_ID")
  CSS_FILE=$(ssh $SSH_OPTS "$SSH_HOST" "ls $REMOTE_WEB/.next/standalone/.next/static/css/ | head -1")
  CSS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://103.22.220.93:3093/_next/static/css/$CSS_FILE")
  echo "Static assets: CSS $CSS_CODE (BUILD_ID: $BUILD_ID)"
else
  echo "DEPLOY FAILED! HTTP $HTTP_CODE"
  ssh $SSH_OPTS "$SSH_HOST" "tail -20 /tmp/nextjs.log"
  exit 1
fi
