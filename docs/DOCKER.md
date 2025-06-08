# Docker Setup for Tracker.gg Valorant API

This document provides comprehensive instructions for running the Tracker.gg Valorant API using Docker.

## Quick Start

### 1. Environment Setup

Create a `.env` file in the project root with your configuration:

```env
# Database Configuration
POSTGRES_USER=valorant_user
POSTGRES_PASSWORD=valorant_pass
POSTGRES_DB=valorant_tracker
POSTGRES_PORT=5432

# API Configuration
API_PORT=8000

# FlareSolverr Configuration
FLARESOLVERR_PORT=8191
FLARESOLVERR_LOG_LEVEL=info
FLARESOLVERR_LOG_HTML=false
FLARESOLVERR_CAPTCHA_SOLVER=none

# Timezone
TIMEZONE=UTC
```

### 2. Start the Full Stack

```bash
# Start API server with database and FlareSolverr
docker-compose up -d

# View logs
docker-compose logs -f app
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **FlareSolverr**: http://localhost:8191

## Service Overview

### Core Services

- **`app`**: Main API server
- **`postgres`**: PostgreSQL database
- **`flaresolverr`**: Cloudflare bypass service

### Optional Services

- **`ingestion`**: Data ingestion service (profile: `ingestion`)

## Docker Commands

### API Server

```bash
# Start API server (default)
docker-compose up -d app

# Start with logs
docker-compose up app

# View API logs
docker-compose logs -f app

# Restart API
docker-compose restart app
```

### Data Ingestion

```bash
# Initialize database only
docker-compose run --rm ingestion init-db

# Load data from ./data directory
docker-compose run --rm ingestion load-data

# Run full setup (init + load data)
docker-compose run --rm ingestion full-setup

# Capture player data
docker-compose run --rm ingestion ingest --capture-player "apolloZ#sun"

# Test connections
docker-compose run --rm ingestion ingest --test-flaresolverr
docker-compose run --rm ingestion ingest --test-scraper
```

### Database Operations

```bash
# Access PostgreSQL directly
docker-compose exec postgres psql -U valorant_user -d valorant_tracker

# Database backup
docker-compose exec postgres pg_dump -U valorant_user valorant_tracker > backup.sql

# Database restore
docker-compose exec -T postgres psql -U valorant_user valorant_tracker < backup.sql

# View database logs
docker-compose logs -f postgres
```

### Development

```bash
# Start with file watching (rebuild on changes)
docker-compose up --build app

# Run development ingestion
docker-compose run --rm ingestion ingest --scrape-player "test#player"

# Execute commands in running container
docker-compose exec app python -m src api --help
docker-compose exec app python -m src ingest --help
```

## Data Persistence

### Volume Mounts

- **`./data:/app/data`**: JSON data files for ingestion
- **`postgres_data`**: PostgreSQL data persistence

### Data Loading

Place your JSON data files in the `./data` directory, and they will be automatically loaded when starting the services.

## Environment Variables

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `valorant_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `valorant_pass` | PostgreSQL password |
| `POSTGRES_DB` | `valorant_tracker` | Database name |
| `POSTGRES_PORT` | `5432` | Database port (host) |

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8000` | API server port (host) |
| `DATABASE_URL` | Auto-generated | Full database connection string |

### FlareSolverr Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLARESOLVERR_PORT` | `8191` | FlareSolverr port (host) |
| `FLARESOLVERR_LOG_LEVEL` | `info` | Log level (debug, info, warn, error) |
| `FLARESOLVERR_LOG_HTML` | `false` | Log HTML responses |
| `FLARESOLVERR_CAPTCHA_SOLVER` | `none` | Captcha solver method |

## Custom Entrypoint Commands

The Docker image supports multiple commands via the entrypoint script:

| Command | Description |
|---------|-------------|
| `api` | Start API server (default) |
| `init-db` | Initialize database only |
| `load-data` | Load data from /app/data |
| `full-setup` | Initialize DB + load data |
| `ingest <args>` | Run ingestion commands |

### Examples

```bash
# Different startup modes
docker run tracker-api:latest api                    # Start API server
docker run tracker-api:latest init-db               # Initialize database
docker run tracker-api:latest load-data             # Load data files
docker run tracker-api:latest full-setup            # Full initialization

# Ingestion commands
docker run tracker-api:latest ingest --help
docker run tracker-api:latest ingest --test-flaresolverr
docker run tracker-api:latest ingest --capture-player "player#tag"
```

## Profiles

### Default Profile

Starts core services (app, postgres, flaresolverr):

```bash
docker-compose up -d
```

### Ingestion Profile

Includes ingestion service for data operations:

```bash
docker-compose --profile ingestion up -d
```

## Troubleshooting

### Common Issues

#### Database Connection

```bash
# Check database health
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test connection manually
docker-compose exec postgres pg_isready -U valorant_user
```

#### FlareSolverr Issues

```bash
# Check FlareSolverr status
curl http://localhost:8191/v1

# View FlareSolverr logs
docker-compose logs flaresolverr

# Restart FlareSolverr
docker-compose restart flaresolverr
```

#### API Issues

```bash
# Check API health
curl http://localhost:8000/health

# View detailed logs
docker-compose logs -f app

# Restart API
docker-compose restart app
```

### Debug Mode

Run services in debug mode with verbose logging:

```bash
# Start with debug environment
FLARESOLVERR_LOG_LEVEL=debug docker-compose up

# Run ingestion with debug output
docker-compose run --rm ingestion ingest --capture-player "player#tag" --output-file debug.json
```

## Production Deployment

### Security Considerations

1. **Change default passwords** in `.env`
2. **Use secrets management** for production
3. **Configure firewall** rules appropriately
4. **Use HTTPS** reverse proxy (nginx, traefik)

### Scaling

```bash
# Scale API service
docker-compose up -d --scale app=3

# Use load balancer
# Configure nginx/traefik for load balancing
```

### Monitoring

```bash
# Monitor resource usage
docker-compose top

# Monitor logs
docker-compose logs -f --tail=100

# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/admin/stats
```

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Complete cleanup
docker system prune -a
``` 