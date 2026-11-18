# Oracle Always Free — Fi Sikkati API

Runs API + worker + PostGIS + Redis + Caddy on one VM. Web stays on Vercel.

## 1. Create the free VM

1. Sign up: https://signup.cloud.oracle.com/
2. Create **Compute → Instance**
   - Image: Ubuntu 22.04/24.04
   - Shape: **VM.Standard.A1.Flex** (Ampere Always Free) — e.g. 2 OCPU / 12 GB
   - Assign a public IP
   - Open ingress **TCP 22, 80, 443** in the VCN security list / NSG
3. SSH in with the private key you downloaded

## 2. Bootstrap Docker

```bash
curl -fsSL https://raw.githubusercontent.com/YousssefEmad/fi-sikkati/develop/infra/oracle/bootstrap-vm.sh | bash
# or copy the script from the repo
newgrp docker
```

## 3. Deploy

```bash
git clone https://github.com/YousssefEmad/fi-sikkati.git
cd fi-sikkati/infra/oracle
cp .env.example .env
# fill AUTH_* secrets + BOOTSTRAP_* emails
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1/health/ready
```

## 4. Point Vercel at the API

Set `API_INTERNAL_URL` to `http://<PUBLIC_IP>` (or `https://api.your-domain` once TLS/domain is ready), then redeploy the web app.

## 5. Smoke test

- `GET /health/ready` → ok
- Register + sign-in on https://fi-sikkati.vercel.app
- `/ar/admin` with a bootstrap admin email
