#!/usr/bin/env bash
# Step 4: Obtain Let's Encrypt certificate
# Run this AFTER deploy-2-setup.sh and AFTER DNS is pointing to the droplet.
set -euo pipefail

DROPLET_IP="${1:?Usage: ./deploy-4-ssl.sh <droplet-ip>}"
DOMAIN="openemr.g4.techopswhiz.com"
EMAIL="${2:-admin@techopswhiz.com}"
SSH="ssh -o StrictHostKeyChecking=accept-new root@$DROPLET_IP"

echo "==> Stopping nginx (if running)..."
$SSH "cd /opt/openemr/docker/production && docker compose stop nginx 2>/dev/null || true"

echo "==> Getting certificate with standalone certbot..."
$SSH "docker run --rm -p 80:80 \
  -v openemr_certbot-certs:/etc/letsencrypt \
  -v openemr_certbot-webroot:/var/www/certbot \
  certbot/certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    -d $DOMAIN"

echo "==> Starting full stack..."
$SSH "cd /opt/openemr/docker/production && docker compose up -d"

echo ""
echo "==> SSL configured! Access:"
echo "    OpenEMR: https://$DOMAIN"
echo "    Agent:   https://$DOMAIN/agent/"
