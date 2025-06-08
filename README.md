# Valorant Tracker.gg Enhanced System

🎯 **Advanced Valorant player statistics system with browser-based data collection and AI-powered insights.**

## ✨ Key Features

### 🌐 **Enhanced Browser-Based Updates**
- **Real Browser Automation**: Uses FlareSolverr to load actual tracker.gg pages in a real browser
- **API Call Interception**: Captures the exact same API calls that tracker.gg makes
- **Anti-Detection Technology**: Smart user agent rotation, realistic delays, and human-like behavior
- **Robust Error Handling**: Graceful handling of rate limits and anti-bot measures

### 🤖 **AI-Powered Analysis**
- **Anthropic Claude Integration**: Advanced AI agent for performance analysis
- **Contextual Insights**: Player-specific recommendations and strategic advice
- **Performance Trends**: Automatic analysis of improvement areas
- **Interactive Chat**: Real-time conversation with AI about player performance

### 🏗️ **Production-Ready Infrastructure**
- **Docker Compose**: Complete containerized setup
- **PostgreSQL Database**: Robust data storage with proper indexing
- **Health Monitoring**: Built-in health checks and status endpoints
- **Auto-Scaling**: Configurable concurrency and resource limits

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- 2GB+ RAM available
- Port 8000, 8191, 5432 available

### 1. One-Command Setup
```bash
# Download and run the setup script
curl -fsSL https://raw.githubusercontent.com/your-repo/valorant-tracker/main/setup.sh | bash -s setup
```

### 2. Manual Setup
```bash
# Clone the repository
git clone https://github.com/your-repo/valorant-tracker.git
cd valorant-tracker

# Make setup script executable
chmod +x setup.sh

# Run initial setup
./setup.sh setup
```

### 3. Verify Installation
```bash
# Check system status
./setup.sh status

# Test functionality
./setup.sh test
```

### 4. Access the System
- **🌐 Web Dashboard**: http://localhost:8000/dashboard
- **📚 API Docs**: http://localhost:8000/docs
- **🔧 FlareSolverr**: http://localhost:8191

---

## 📖 Usage Guide

### Updating Player Data

#### Via Web Dashboard
1. Visit http://localhost:8000/dashboard
2. Enter a Riot ID (e.g., `TenZ#tenz`)
3. Click "Search" to view existing data
4. Click "Update Data" for fresh information

#### Via API
```bash
# Update a single player
curl -X POST "http://localhost:8000/players/TenZ%23tenz/update"

# Bulk update multiple players
curl -X POST "http://localhost:8000/players/bulk-update" \
  -H "Content-Type: application/json" \
  -d '{"riot_ids": ["TenZ#tenz", "s0m#000"], "max_concurrent": 2}'
```

#### Via Command Line
```bash
# Update using the management script
./setup.sh update "TenZ#tenz"
```

### AI Analysis Features

#### Chat with AI Agent
```bash
# Via API
curl -X POST "http://localhost:8000/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze TenZ performance", 
    "player_context": "TenZ#tenz"
  }'
```

#### Common AI Queries
- "What are this player's strengths and weaknesses?"
- "How can they improve their gameplay?"
- "Compare their recent performance to overall stats"
- "What playlist should they focus on?"

### Data Access

#### Premier League Stats (Primary Goal)
```bash
# Get Premier stats for a player
curl "http://localhost:8000/players/TenZ%23tenz/premier"
```

#### All Playlist Data
```bash
# Get all playlists
curl "http://localhost:8000/players/TenZ%23tenz/playlists"

# Get specific playlist
curl "http://localhost:8000/players/TenZ%23tenz/playlists/competitive"
```

#### Performance Timeline
```bash
# Get recent performance data
curl "http://localhost:8000/players/TenZ%23tenz/heatmap?days=30"
```

---

## 🛠️ System Management

### Service Control
```bash
./setup.sh start      # Start all services
./setup.sh stop       # Stop all services
./setup.sh restart    # Restart all services
./setup.sh status     # Check system status
```

### Monitoring and Logs
```bash
./setup.sh logs app           # API service logs
./setup.sh logs flaresolverr  # Browser automation logs
./setup.sh logs postgres      # Database logs
```

### Maintenance
```bash
./setup.sh backup    # Create database backup
./setup.sh test      # Test system functionality
./setup.sh clean     # Clean up Docker resources
```

---

## ⚙️ Configuration

### Environment Variables (.env file)
```bash
# Database
POSTGRES_USER=valorant_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=valorant_tracker

# Services
API_PORT=8000
FLARESOLVERR_PORT=8191

# AI Features (Required for AI agent)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Advanced Settings
FLARESOLVERR_LOG_LEVEL=info
BROWSER_TIMEOUT=40000
```

### Docker Compose Profiles
```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Start with caching
docker-compose --profile redis up -d

# Start ingestion service
docker-compose --profile ingestion up -d
```

---

## 🔧 Advanced Features

### Bulk Operations
```python
# Python example for bulk updates
import asyncio
import aiohttp

async def bulk_update_team(player_ids):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for player_id in player_ids:
            task = session.post(f"http://localhost:8000/players/{player_id}/update")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

# Update entire team
team_players = ["TenZ#tenz", "Zellsis#000", "johnqt#000"]
asyncio.run(bulk_update_team(team_players))
```

### Custom Data Processing
```python
# Access raw database for custom analysis
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine("postgresql://valorant_user:password@localhost:5432/valorant_tracker")

# Get all Premier stats
query = """
SELECT p.riot_id, prem.*, h.date, h.kd_ratio, h.adr 
FROM players p 
JOIN player_segments ps ON p.id = ps.player_id 
JOIN premier_data prem ON ps.id = prem.segment_id
JOIN heatmap_data h ON p.id = h.player_id 
WHERE ps.playlist = 'premier'
"""

df = pd.read_sql(query, engine)
```

### Monitoring Integration
```bash
# Start with monitoring stack
docker-compose --profile monitoring up -d

# Access Grafana dashboards
open http://localhost:3000  # admin/admin
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. FlareSolverr Not Starting
```bash
# Check FlareSolverr logs
./setup.sh logs flaresolverr

# Common fix: Increase memory
# Edit docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 3G
```

#### 2. Rate Limiting from Tracker.gg
```bash
# Check update status
curl http://localhost:8000/admin/update-status

# Wait 5-10 minutes between updates
# System automatically handles rate limiting
```

#### 3. Database Connection Issues
```bash
# Check database health
./setup.sh status

# Reset database
docker-compose down postgres
docker volume rm valorant-tracker_postgres_data
./setup.sh start
```

#### 4. Memory Issues
```bash
# Monitor resource usage
docker stats

# Increase Docker memory limit (Docker Desktop)
# Or add swap space on Linux
```

### Debug Mode
```bash
# Enable debug logging
export FLARESOLVERR_LOG_LEVEL=debug
export LOG_LEVEL=DEBUG

# Restart services
./setup.sh restart
```

### System Health Check
```bash
# Comprehensive system test
./setup.sh test

# Check individual components
curl http://localhost:8000/health
curl http://localhost:8191/v1 -X POST -d '{"cmd":"sessions.list"}'
```

---

## 📊 Performance Optimization

### For High-Volume Usage

#### 1. Increase Concurrency
```yaml
# docker-compose.yml
services:
  app:
    environment:
      - MAX_WORKERS=4
      - DB_POOL_SIZE=20
```

#### 2. Enable Caching
```bash
# Start Redis cache
docker-compose --profile redis up -d
```

#### 3. Database Tuning
```yaml
# docker-compose.yml - PostgreSQL optimization
services:
  postgres:
    command: |
      postgres
      -c max_connections=200
      -c shared_buffers=512MB
      -c effective_cache_size=2GB
```

#### 4. FlareSolverr Scaling
```yaml
# Run multiple FlareSolverr instances
services:
  flaresolverr-1:
    image: ghcr.io/flaresolverr/flaresolverr:latest
    ports: ["8191:8191"]
  flaresolverr-2:
    image: ghcr.io/flaresolverr/flaresolverr:latest
    ports: ["8192:8191"]
```

---

## 🤝 Contributing

### Development Setup
```bash
# Clone for development
git clone https://github.com/your-repo/valorant-tracker.git
cd valorant-tracker

# Create development environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run in development mode
./setup.sh start
export ENVIRONMENT=development
python -m src api --reload
```

### Adding New Features
1. **New API Endpoints**: Edit `src/expose/api.py`
2. **Database Models**: Update `src/shared/database.py`
3. **AI Agent Features**: Modify `src/ai_agent/anthropic_agent.py`
4. **Update Logic**: Enhance `src/ingest/enhanced_tracker_updater.py`

### Testing
```bash
# Run tests
pytest tests/

# Test API endpoints
./setup.sh test

# Test specific player update
./setup.sh update "test#user"
```

---

## 📄 API Reference

### Core Endpoints

#### Player Management
- `GET /players` - List all players
- `GET /players/{riot_id}` - Get player info
- `POST /players/{riot_id}/update` - Update player data
- `POST /players/bulk-update` - Update multiple players

#### Data Access
- `GET /players/{riot_id}/premier` - Premier league stats
- `GET /players/{riot_id}/playlists` - All playlist data
- `GET /players/{riot_id}/heatmap` - Performance timeline
- `GET /players/{riot_id}/loadouts` - Weapon statistics

#### AI Features
- `POST /ai/chat` - Chat with AI agent
- `POST /ai/chat/stream` - Streaming AI responses
- `POST /ai/reset` - Reset conversation
- `GET /ai/history` - Get chat history

#### System Management
- `GET /health` - System health check
- `GET /admin/update-status` - Update system status
- `POST /admin/test-update` - Test update functionality
- `GET /admin/stats` - Database statistics

### Authentication
Currently, the system runs without authentication for simplicity. For production use:

```python
# Add API key authentication
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != "your-secret-api-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
```

---

## 🌟 Roadmap

### Planned Features
- [ ] **Team Analysis**: Multi-player team performance tracking
- [ ] **Tournament Mode**: Special handling for tournament data
- [ ] **Webhook Integration**: Real-time notifications for updates
- [ ] **Advanced Analytics**: ML-powered performance predictions
- [ ] **Discord Bot**: Direct Discord integration for team stats
- [ ] **Mobile API**: Optimized endpoints for mobile apps

### Contributing
We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with tests
4. Update documentation

---

## 📞 Support

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check this README and API docs
- **System Logs**: Use `./setup.sh logs [service]` for debugging

### Common Questions

**Q: Why use browser automation instead of direct API calls?**
A: Tracker.gg has anti-bot protection. Browser automation ensures we get the same data as a real user.

**Q: How often should I update player data?**
A: The system handles rate limiting automatically. For active players, every 2-4 hours is recommended.

**Q: Can I run this on a server?**
A: Yes! The Docker setup works on any Linux server. Just ensure ports 8000, 8191, and 5432 are available.

**Q: Is this legal?**
A: Yes, we're accessing publicly available data in a respectful way with proper rate limiting.

---

## 📜 License

MIT License - feel free to use this for personal or commercial projects.

---

**Built with ❤️ for the Valorant community**

*For the latest updates and advanced features, star this repository and follow our development!*