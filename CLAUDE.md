# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management
- **Primary**: `uv` with `pyproject.toml` and `uv.lock`
- Install dependencies: `uv sync`
- Add dependencies: `uv add <package>`
- Run Python: `uv run python -m src`

### Code Quality
- Format code: `uv run black src/`
- Sort imports: `uv run isort src/`  
- Type checking: `uv run mypy src/`
- Run tests: `uv run pytest tests/`

### Application Management
```bash
# Development mode
uv run python -m src api --reload --port 8000

# CLI usage  
uv run python -m src ingest --scrape-player "username#tag"

# System management (production)
./setup.sh start     # Start all Docker services
./setup.sh status    # Check system health
./setup.sh logs app  # View API logs
./setup.sh test      # Test functionality
```

### Docker Commands
```bash
# Full stack
docker-compose up -d

# Specific services
docker-compose up -d postgres flaresolverr
docker-compose logs -f app
```

## Architecture Overview

### Core Components
- **Data Ingestion** (`src/ingest/`): FlareSolverr-based web scraping that captures real tracker.gg API calls
- **API Layer** (`src/expose/`): FastAPI application with REST endpoints and web dashboard  
- **AI Integration** (`src/ai_agent/`): Anthropic Claude agent with MCP server for performance analysis
- **Shared Core** (`src/shared/`): Database models, utilities, and common functionality

### Key Design Patterns
- **Browser Automation**: Uses FlareSolverr (browser automation) to bypass tracker.gg anti-bot protection
- **Endpoint Prioritization**: Critical endpoints (competitive/premier) have higher update priority than casual modes
- **Database-First**: All scraped data flows through SQLModel/PostgreSQL before API exposure
- **AI Context**: Player data feeds into Claude agent for contextual performance insights

### Data Flow
1. **Scraping**: `tracker-gg.py` uses FlareSolverr to capture tracker.gg API responses
2. **Processing**: `data_loader.py` transforms JSON into SQLModel database records
3. **Storage**: PostgreSQL stores structured player statistics, match data, loadouts
4. **API**: FastAPI exposes data via REST endpoints with automatic validation
5. **AI**: Claude agent analyzes data to provide performance insights and recommendations

### Update Modes
- **Init Mode**: Full data discovery for new players (15-30 min, all endpoints)
- **Update Mode**: Priority endpoints only for regular refreshes (2-5 min)  
- **Full Mode**: Complete API grammar testing for research/debugging

## File Organization

### Main Modules
- `src/ingest/tracker-gg.py`: Core scraper with endpoint prioritization and rate limiting
- `src/ingest/data_loader.py`: Database loading with unified data transformation
- `src/expose/api.py`: FastAPI application with player endpoints and AI chat
- `src/shared/models.py`: Comprehensive Pydantic models for all tracker.gg data structures
- `src/shared/database.py`: SQLModel schemas and database connection management
- `src/ai_agent/anthropic_agent.py`: Claude integration for player analysis

### Configuration
- `pyproject.toml`: Primary dependency definition with uv support
- `docker-compose.yml`: Full production stack configuration
- `setup.sh`: System management script for Docker operations
- `.env`: Environment variables for database, API keys, service ports

## Development Guidelines

### Adding New Endpoints
1. Define Pydantic response models in `src/shared/models.py`
2. Add database schemas in `src/shared/database.py` if needed
3. Implement endpoint logic in `src/expose/api.py`
4. Follow existing patterns for player ID validation and error handling

### Database Changes
- Use SQLModel for all database schemas with proper relationships
- Database operations should be async using SQLModel's async session
- Follow the player -> segments -> data hierarchy for new tables

### Scraping Modifications
- Respect `ENDPOINT_PRIORITIES` dictionary for update frequency
- Use `TIMING_CONFIG` for all delays and retry logic
- Always test changes with single player before bulk operations
- Follow browser automation best practices to avoid detection

### AI Agent Updates
- Extend `anthropic_agent.py` for new analysis capabilities
- Use MCP tools for database access within agent context
- Maintain conversation context for multi-turn player analysis
- Follow Claude API best practices for token management

## Common Pitfalls

### Rate Limiting
- Tracker.gg has aggressive rate limiting - always use proper delays
- FlareSolverr sessions must be properly cleaned up to avoid resource leaks
- Use priority updates for regular data refresh, not full discovery

### Database Performance  
- Player lookups should use indexed riot_id field
- Bulk operations require proper transaction handling
- Use database connection pooling for concurrent requests

### Browser Automation
- FlareSolverr requires significant memory (2GB+ recommended)
- Session management is critical - always destroy sessions after use
- Real user agent strings and realistic delays are essential for avoiding blocks