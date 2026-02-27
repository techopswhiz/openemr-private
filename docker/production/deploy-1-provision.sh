#!/usr/bin/env bash
# Step 1: Provision DigitalOcean droplet, SSH key, and firewall
set -euo pipefail

DROPLET_NAME="openemr-prod"
REGION="sfo3"
SIZE="s-2vcpu-4gb"
IMAGE="ubuntu-24-04-x64"
SSH_KEY_PATH="$HOME/.ssh/id_ed25519.pub"
DOMAIN="openemr.g4.techopswhiz.com"

echo "==> Uploading SSH key to DigitalOcean..."
KEY_ID=$(doctl compute ssh-key import "$DROPLET_NAME-key" \
  --public-key-file "$SSH_KEY_PATH" \
  --format ID --no-header 2>/dev/null || \
  doctl compute ssh-key list --format ID,Name --no-header | grep "$DROPLET_NAME-key" | awk '{print $1}')
echo "    SSH key ID: $KEY_ID"

echo "==> Creating droplet..."
doctl compute droplet create "$DROPLET_NAME" \
  --region "$REGION" \
  --size "$SIZE" \
  --image "$IMAGE" \
  --ssh-keys "$KEY_ID" \
  --wait \
  --format ID,Name,PublicIPv4 --no-header
echo ""

DROPLET_IP=$(doctl compute droplet get "$DROPLET_NAME" --format PublicIPv4 --no-header)
DROPLET_ID=$(doctl compute droplet get "$DROPLET_NAME" --format ID --no-header)
echo "    Droplet IP: $DROPLET_IP"

echo "==> Creating firewall..."
doctl compute firewall create \
  --name "$DROPLET_NAME-fw" \
  --droplet-ids "$DROPLET_ID" \
  --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0,address:::/0 protocol:tcp,ports:80,address:0.0.0.0/0,address:::/0 protocol:tcp,ports:443,address:0.0.0.0/0,address:::/0 protocol:icmp,address:0.0.0.0/0,address:::/0" \
  --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0,address:::/0 protocol:udp,ports:all,address:0.0.0.0/0,address:::/0 protocol:icmp,address:0.0.0.0/0,address:::/0" \
  --format ID,Name --no-header
echo ""

echo "==> Done! Next steps:"
echo "    1. Point DNS: $DOMAIN -> $DROPLET_IP"
echo "    2. Run: ./deploy-2-setup.sh $DROPLET_IP"
