#!/usr/bin/env bash
# Step 3: Verify all services are running
set -euo pipefail

DROPLET_IP="${1:?Usage: ./deploy-3-verify.sh <droplet-ip>}"
DOMAIN="openemr.g4.techopswhiz.com"
SSH="ssh -o StrictHostKeyChecking=accept-new root@$DROPLET_IP"

echo "==> Checking container status..."
$SSH "cd /opt/openemr/docker/production && docker compose ps"

echo ""
echo "==> Checking OpenEMR health..."
$SSH "curl -sf --insecure https://localhost/meta/health/readyz" && echo " OK" || echo " WAITING (may still be initializing)"

echo ""
echo "==> Checking agent health..."
$SSH "curl -sf http://localhost:8080/health" && echo " OK" || echo " WAITING (depends on OpenEMR)"

echo ""
echo "==> URLs:"
echo "    OpenEMR:  http://$DOMAIN (admin/pass)"
echo "    Agent:    http://$DOMAIN:8080"
echo ""
echo "==> After logging in, register an OAuth2 client:"
echo "    Admin > System > API Clients"
echo "    Then update .env with client_id/secret and run:"
echo "    ssh root@$DROPLET_IP 'cd /opt/openemr/docker/production && docker compose restart agent'"
