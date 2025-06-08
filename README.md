# Tracker.gg Valorant API

A comprehensive Python application that captures and exposes Valorant player statistics from tracker.gg. Features a modular architecture with separate ingestion and API modules, supporting both web scraping and direct API data capture.

## Architecture Overview

The application is organized into three main modules:

- **`src/shared`** - Common models, database logic, and utilities
- **`src/ingest`** - Data ingestion components (scrapers, API capture, data loading)
- **`src/expose`** - FastAPI application for exposing the ingested data

## Features

### Data Ingestion
- **FlareSolverr Integration**: Bypasses Cloudflare protection on tracker.gg
- **Direct API Capture**: Captures data from tracker.gg's internal API endpoints
- **Web Scraping**: HTML parsing for additional profile information
- **Bulk Data Loading**: Processes multiple JSON files from data captures
- **Comprehensive Coverage**: Supports all playlists (Competitive, Premier, Unrated, etc.)

### Data Storage
- **SQLModel/PostgreSQL**: Type-safe database models with Pydantic validation
- **Comprehensive Statistics**: Stores individual stat values with metadata
- **Timeline Data**: Heatmap/timeline data for performance tracking
- **Data Lineage**: Tracks ingestion operations and source files

### REST API
- **FastAPI**: Modern, fast API framework with automatic documentation
- **Premier Endpoint**: Dedicated `/players/{riot_id}/premier` endpoint (main goal)
- **Comprehensive Endpoints**: Access to all playlists, statistics, and timeline data
- **Admin Endpoints**: Database statistics and ingestion logs

## Requirements

- Python 3.8+
- PostgreSQL
- FlareSolverr (Docker container)

## Installation

1. **Clone and Setup**:
```bash
git clone <repository-url>
cd tracker-gg-api
pip install -r requirements.txt
```

2. **Start FlareSolverr**:
```bash
docker run -d \
  --name flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  --restart unless-stopped \
  ghcr.io/flaresolverr/flaresolverr:latest
```

3. **Setup Database**:
```bash
# Set database URL (modify as needed)
export DATABASE_URL="postgresql://valorant_user:valorant_pass@localhost:5432/valorant_tracker"

# Initialize database
python -m src ingest --init-db
```

## Usage

### Data Ingestion

**Test Connections**:
```bash
# Test FlareSolverr connection
python -m src ingest --test-flaresolverr

# Test scraper functionality
python -m src ingest --test-scraper
```

**Capture Player Data**:
```bash
# Capture API data for a specific player
python -m src ingest --capture-player "apolloZ#sun" --output-file "apolloZ_data.json"

# Full scrape (web + API data)
python -m src ingest --scrape-player "username#tag" --output-file "player_data.json"
```

**Load Data into Database**:
```bash
# Load a single JSON file
python -m src ingest --load-file "apolloZ_data.json"

# Load entire data directory
python -m src ingest --load-directory "./data"
```

### API Server

**Start the API**:
```bash
# Production
python -m src api

# Development with auto-reload
python -m src api --reload --port 8080
```

**API Documentation**: Visit `http://localhost:8000/docs` for interactive documentation.

### Key API Endpoints

**Premier Data (Main Goal)**:
```bash
# Get Premier playlist data
curl "http://localhost:8000/players/apolloZ%23sun/premier"
```

**Player Information**:
```bash
# List all players
curl "http://localhost:8000/players"

# Get player info
curl "http://localhost:8000/players/apolloZ%23sun"

# Get all playlists
curl "http://localhost:8000/players/apolloZ%23sun/playlists"

# Get specific playlist
curl "http://localhost:8000/players/apolloZ%23sun/playlists/competitive"
```

**Timeline and Performance**:
```bash
# Get heatmap/timeline data
curl "http://localhost:8000/players/apolloZ%23sun/heatmap?playlist=premier&days=30"

# Get loadout statistics
curl "http://localhost:8000/players/apolloZ%23sun/loadouts"
```

**Admin Endpoints**:
```bash
# Database statistics
curl "http://localhost:8000/admin/stats"

# Ingestion logs
curl "http://localhost:8000/admin/ingestion-logs"
```

## Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL="postgresql://user:pass@localhost:5432/valorant_tracker"

# FlareSolverr URL (if not default)
FLARESOLVERR_URL="http://localhost:8191"
```

### Database Schema

The application uses SQLModel for type-safe database operations:

- **Players**: Unique riot IDs with metadata
- **PlayerSegments**: Playlist/loadout segments with stats
- **StatisticValues**: Individual statistics with display information
- **HeatmapData**: Timeline performance data
- **DataIngestionLog**: Audit trail for data operations

## Architecture Details

### Shared Components (`src/shared`)
- **`models.py`**: Pydantic models for all tracker.gg API responses
- **`database.py`**: SQLModel database models and connection logic

### Ingestion Components (`src/ingest`)
- **`flaresolverr_client.py`**: FlareSolverr integration for Cloudflare bypass
- **`valorant_scraper.py`**: Web scraping and API capture functionality
- **`data_loader.py`**: Bulk loading of JSON files into database

### API Components (`src/expose`)
- **`api.py`**: Complete FastAPI application with all endpoints

## Data Flow

1. **Capture**: Use FlareSolverr to bypass Cloudflare and capture tracker.gg API data
2. **Store**: Save captured data as JSON files for processing
3. **Load**: Process JSON files and load into PostgreSQL database
4. **Expose**: Serve data via FastAPI with comprehensive REST endpoints

## Development

### Project Structure
```
tracker-gg-api/
├── src/
│   ├── shared/          # Common models and database logic
│   ├── ingest/          # Data ingestion components
│   ├── expose/          # API endpoints
│   └── __main__.py      # CLI entry point
├── data/                # JSON data files
├── scripts/             # Utility scripts
├── requirements.txt
└── docker-compose.yml
```

### Testing Components

```bash
# Test individual components
python -m src.ingest.flaresolverr_client --test-connection
python -m src.ingest.valorant_scraper --test-connection
python -m src.ingest.data_loader --init-db

# Full integration test
python -m src ingest --scrape-player "test#player"
python -m src ingest --load-file "test_data.json"
python -m src api --reload
```

## Performance

- **Database Optimization**: Proper indexes for fast queries
- **API Performance**: SQLModel for efficient database operations
- **Data Validation**: Pydantic models ensure data integrity
- **Async Support**: FastAPI async endpoints for scalability

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the modular architecture
4. Add tests for new functionality
5. Submit a pull request

---

**Main Goal Achieved**: The `/players/{riot_id}/premier` endpoint provides direct access to Premier playlist data as requested, with comprehensive support for all tracker.gg statistics and timeline data.
