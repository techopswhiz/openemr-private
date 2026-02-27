#!/usr/bin/env bash
# Step 2: Install Docker and deploy the stack on the droplet
set -euo pipefail

DROPLET_IP="${1:?Usage: ./deploy-2-setup.sh <droplet-ip>}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSH="ssh -o StrictHostKeyChecking=accept-new root@$DROPLET_IP"

echo "==> Installing Docker on droplet..."
$SSH "apt-get update -qq && apt-get upgrade -y -qq && \
  apt-get install -y -qq docker.io docker-compose-v2 && \
  systemctl enable --now docker"

echo "==> Syncing code to droplet..."
rsync -az --delete \
  --include='agent/***' \
  --include='docker/' \
  --include='docker/production/***' \
  --exclude='docker/production/.env' \
  --exclude='*' \
  -e "ssh -o StrictHostKeyChecking=accept-new" \
  "$REPO_ROOT/" "root@$DROPLET_IP:/opt/openemr/"

# Copy .env only if it doesn't exist on the droplet yet
$SSH "test -f /opt/openemr/docker/production/.env" || \
  scp -o StrictHostKeyChecking=accept-new \
    "$(dirname "$0")/.env" "root@$DROPLET_IP:/opt/openemr/docker/production/.env"

echo "==> Starting the stack (this takes a few minutes)..."
$SSH "cd /opt/openemr/docker/production && docker compose up -d --build"

echo ""
echo "==> Stack is starting. Monitor with:"
echo "    ssh root@$DROPLET_IP 'docker compose -f /opt/openemr/docker/production/docker-compose.yml logs -f'"
echo ""
echo "==> Once healthy, run: ./deploy-3-verify.sh $DROPLET_IP"
