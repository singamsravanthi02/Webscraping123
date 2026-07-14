# Deployment Guide

This guide covers deploying the SPIP (Sreyas Placement Intelligence Platform) using Docker Compose.

## Prerequisites
- A cloud server (Ubuntu 22.04 recommended) with at least 4GB RAM.
- `docker` and `docker-compose` installed.
- Domain name mapped to your server's IP address (e.g., `spip.sreyas.ac.in`).

## 1. Clone and Configure
1. SSH into your server: `ssh root@your_ip`
2. Clone the repository.
3. Copy `.env.example` to `.env` in both `frontend/` and `backend/`.
4. Update `.env` with production secrets (Postgres passwords, JWT secret, Gemini API key, etc.).

## 2. Docker Compose Build
Run the following command in the root directory where `docker-compose.yml` is located:
```bash
docker-compose up -d --build
```
This will spin up:
- `spip_db` (Postgres)
- `spip_redis` (Redis)
- `spip_qdrant` (Qdrant Vector DB)
- `spip_backend` (FastAPI at :8000)
- `spip_celery` (Celery Worker)
- `spip_frontend` (Next.js at :3000)
- `spip_prometheus` (Metrics Aggregator)
- `spip_grafana` (Observability Dashboard at :3001)

### Observability Dashboard
Once running, navigate to `http://your_ip:3001` to access Grafana.
- **Username**: `admin`
- **Password**: `admin` (change on first login)

## 3. Reverse Proxy (Nginx)
Install Nginx and configure it to reverse proxy port 80/443 to your frontend (port 3000) and `/api` to your backend (port 8000).

```nginx
server {
    server_name spip.sreyas.ac.in;

    location /api/ {
        proxy_pass http://localhost:8000/api/;
    }

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

## 4. Database Migrations
Run the Alembic migrations inside the running backend container:
```bash
docker exec -it spip_backend alembic upgrade head
```

## 5. SSL Certificate
Use Certbot to secure your domain:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d spip.sreyas.ac.in
```

## 6. Zero-Downtime Rollback Strategy
If a new deployment introduces critical bugs, you can rapidly rollback using Docker Image Tagging.
1. Identify the previous working image hash (e.g., `spip_backend:v1.0.4`).
2. Update the `docker-compose.yml` image tag explicitly.
3. Run `docker-compose up -d` to hot-swap the containers.
4. If a database migration caused the issue, downgrade via Alembic:
   ```bash
   docker exec -it spip_backend alembic downgrade -1
   ```
