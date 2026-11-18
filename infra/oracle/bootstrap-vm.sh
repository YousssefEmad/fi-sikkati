#!/usr/bin/env bash
# Run once on a fresh Oracle Ubuntu VM as a sudo-capable user.
set -euo pipefail

sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"

echo "Docker installed. Log out/in (or newgrp docker), then:"
echo "  git clone <repo> && cd fi-sikkati/infra/oracle"
echo "  cp .env.example .env && edit secrets"
echo "  docker compose up -d --build"
