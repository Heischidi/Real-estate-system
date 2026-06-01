# 🏠 Nigerian Real Estate Alert Platform

A production-ready SaaS-style platform that automatically scrapes Nigerian property listings and delivers instant Telegram alerts to subscribers.

---

## Features

- **Multi-source scraping** — PropertyPro, Nigeria Property Centre, PrivateProperty, Property24
- **Plugin architecture** — drop a new scraper file to add a new source
- **Telegram bot** — full subscription flow with inline keyboards
- **Instant alerts** — matched listings delivered the moment they're discovered
- **Admin API** — JWT-protected endpoints for monitoring and control
- **Prometheus metrics** — scraper performance, alert counts, subscriber stats
- **Docker Compose** — one command to run all 7 services

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy async |
| Cache/Queue | Redis 7 |
| Tasks | Celery + Celery Beat |
| Scraping | Playwright (Chromium) + BeautifulSoup |
| Bot | python-telegram-bot v21 |
| Proxy | Nginx |
| Monitoring | Prometheus + Grafana |

---

## Quick Start (Docker)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/nigeria-realestate-alerts.git
cd nigeria-realestate-alerts

cp .env.example .env
# Edit .env — fill in all required values
nano .env
```

### 2. Create a Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token into `.env` as `TELEGRAM_BOT_TOKEN`

### 3. Start all services

```bash
docker compose up -d
```

Services will start in order: postgres → redis → migrate (runs migrations) → api → celery → celery-beat → telegram-bot → nginx.

### 4. Verify everything is running

```bash
curl http://localhost/health
# Expected: {"status": "healthy", "database": "ok", ...}

docker compose logs -f telegram-bot
# Should show: telegram_bot_starting
```

---

## Local Development

### Prerequisites
- Python 3.12+
- PostgreSQL 16
- Redis 7
- Playwright Chromium

### Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
playwright install chromium

cp .env.example .env
# Set DATABASE_URL to your local PostgreSQL

alembic upgrade head
uvicorn app.main:app --reload
```

### Run the bot locally

```bash
python -m app.bot.main
```

### Run tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | App secret key (≥32 chars) |
| `DATABASE_URL` | ✅ | PostgreSQL async URL |
| `REDIS_URL` | ✅ | Redis connection URL |
| `CELERY_BROKER_URL` | ✅ | Celery broker (Redis) |
| `CELERY_RESULT_BACKEND` | ✅ | Celery results (Redis) |
| `TELEGRAM_BOT_TOKEN` | ✅ | From @BotFather |
| `ADMIN_USERNAME` | ✅ | Admin API username |
| `ADMIN_PASSWORD` | ✅ | Admin API password (≥8 chars) |
| `JWT_SECRET_KEY` | ✅ | JWT signing secret (≥32 chars) |
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL password |
| `SCRAPER_REQUEST_DELAY_SECONDS` | ⬜ | Seconds between requests (default: 5.0) |
| `SCRAPE_INTERVAL_MINUTES` | ⬜ | How often to scrape (default: 15) |
| `DISABLED_SCRAPERS` | ⬜ | Comma-separated list of scrapers to skip |
| `PLAYWRIGHT_HEADLESS` | ⬜ | `true` in production (default: true) |
| `NOTIFICATION_RETENTION_DAYS` | ⬜ | Days to keep notification logs (default: 90) |
| `METRICS_ENABLED` | ⬜ | Enable Prometheus metrics (default: true) |

---

## API Reference

OpenAPI docs available at: `http://localhost/docs`

### Public Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness + DB health check |
| `GET` | `/listings` | Browse listings with filters |

**Listing filters**: `city`, `property_type`, `min_price`, `max_price`, `source`, `page`, `page_size`

### Admin Endpoints (JWT required)

Get a token first:
```bash
curl -X POST http://localhost/auth/token \
  -d "username=admin&password=yourpassword"
```

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/token` | Get JWT token |
| `GET` | `/subscribers` | List all subscribers |
| `POST` | `/scrape` | Manually trigger scrape |
| `GET` | `/scrape/status` | View registered scrapers |
| `GET` | `/stats` | Platform statistics |

---

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Show welcome message and main menu |
| `/subscribe` | Set up property alerts (guided flow) |
| `/mysettings` | View your current preferences |
| `/unsubscribe` | Stop receiving alerts |
| `/cities` | List supported cities |
| `/help` | Show help message |

### Subscription Flow

```
/subscribe
  → Choose city: Abuja | Lagos | Port Harcourt | Kano
  → Choose property type: Apartment | Flat | Duplex | ...
  → Enter minimum budget (e.g. 5000000)
  → Enter maximum budget (e.g. 80000000)
  → Confirm → Saved!
```

---

## Adding a New Scraper

1. Create `app/scrapers/my_new_site.py`
2. Extend `BaseScraper`, implement `name`, `base_url`, and `scrape()`
3. Add `_registry["my_new_site"] = MyNewSiteScraper` at the bottom
4. Import the module in `app/scrapers/registry.py`'s `_autodiscover()` function

That's it — the scraper will be automatically included in every scrape cycle.

---

## Ubuntu VPS Production Deployment Guide

### Server Requirements
- Ubuntu 22.04 LTS
- Minimum: 4 vCPU, 8 GB RAM, 50 GB SSD
- Open ports: 80, 443

### Initial Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Log out and back in for group changes
```

### Deploy

```bash
# Clone project
git clone https://github.com/your-org/nigeria-realestate-alerts.git /opt/realestate
cd /opt/realestate

# Configure environment
cp .env.example .env
nano .env  # Fill in all values

# Start services
docker compose up -d

# Check status
docker compose ps
docker compose logs -f api
```

### SSL/HTTPS with Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com

# Update nginx.conf to uncomment the HTTP -> HTTPS redirect
# Then restart nginx:
docker compose restart nginx
```

### Systemd Auto-restart (optional)

```bash
sudo nano /etc/systemd/system/realestate.service
```

```ini
[Unit]
Description=Nigerian Real Estate Alert Platform
Requires=docker.service
After=docker.service

[Service]
WorkingDirectory=/opt/realestate
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable realestate
sudo systemctl start realestate
```

### Monitoring

```bash
# View logs
docker compose logs -f --tail=100

# Check Celery task queue
docker compose exec redis redis-cli llen celery

# View scraper stats
curl -H "Authorization: Bearer <token>" http://localhost/stats
```

---

## ⚠️ Ethical Scraping Policy

This platform is built with the following principles:

1. **Rate limiting is mandatory** — minimum 5 seconds between requests per domain
2. **robots.txt is checked** — scrapers won't access disallowed paths
3. **No aggressive crawling** — max 2 pages per city per scraper per run
4. **Consider partnerships** — for production SaaS use, contact PropertyPro, NPC, PrivateProperty, and Property24 for official API/data access
5. **Review terms of service** before enabling scrapers for commercial use

---

## License

MIT License — see LICENSE file.
