#!/bin/bash

# Valorant Tracker.gg System Setup and Management Script
# This script helps you set up and manage the enhanced tracker system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
DATA_DIR="${SCRIPT_DIR}/data"
LOGS_DIR="${SCRIPT_DIR}/logs"
BACKUPS_DIR="${SCRIPT_DIR}/backups"

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "=================================="
    echo "  Valorant Tracker.gg System"
    echo "  Enhanced Browser-Based Updates"
    echo "=================================="
    echo -e "${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_status "Dependencies check passed ✓"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$BACKUPS_DIR"
    mkdir -p "${SCRIPT_DIR}/monitoring/prometheus"
    mkdir -p "${SCRIPT_DIR}/monitoring/grafana/dashboards"
    mkdir -p "${SCRIPT_DIR}/monitoring/grafana/datasources"
    mkdir -p "${SCRIPT_DIR}/scripts"
    
    print_status "Directories created ✓"
}

# Create default environment file
create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_status "Creating default .env file..."
        
        cat > "$ENV_FILE" << 'EOF'
# Database Configuration
POSTGRES_USER=valorant_user
POSTGRES_PASSWORD=valorant_pass_$(openssl rand -hex 8)
POSTGRES_DB=valorant_tracker
POSTGRES_PORT=5432

# API Configuration
API_PORT=8000

# FlareSolverr Configuration
FLARESOLVERR_PORT=8191
FLARESOLVERR_LOG_LEVEL=info
FLARESOLVERR_LOG_HTML=false
FLARESOLVERR_CAPTCHA_SOLVER=none

# Optional Services
REDIS_PORT=6379
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=admin

# System Configuration
TIMEZONE=UTC

# AI Agent Configuration (Required for AI features)
ANTHROPIC_API_KEY=your_api_key_here

# Advanced FlareSolverr Settings
BROWSER_TIMEOUT=40000
NODE_OPTIONS=--max-old-space-size=2048
EOF
        
        # Generate a random password
        RANDOM_PASS=$(openssl rand -hex 12)
        sed -i "s/valorant_pass_[a-f0-9]*/valorant_pass_${RANDOM_PASS}/g" "$ENV_FILE"
        
        print_status ".env file created with random password ✓"
        print_warning "Please edit .env file and add your ANTHROPIC_API_KEY for AI features"
    else
        print_status ".env file already exists ✓"
    fi
}

# Create backup script
create_backup_script() {
    BACKUP_SCRIPT="${SCRIPT_DIR}/scripts/backup.sh"
    
    if [ ! -f "$BACKUP_SCRIPT" ]; then
        print_status "Creating backup script..."
        
        cat > "$BACKUP_SCRIPT" << 'EOF'
#!/bin/bash

# Database backup script
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/valorant_tracker_${TIMESTAMP}.sql"

echo "Starting database backup at $(date)"

# Create backup
pg_dump -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    
    # Compress the backup
    gzip "$BACKUP_FILE"
    echo "Backup compressed: ${BACKUP_FILE}.gz"
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "valorant_tracker_*.sql.gz" -mtime +7 -delete
    echo "Old backups cleaned up"
else
    echo "Backup failed!" >&2
    exit 1
fi
EOF
        
        chmod +x "$BACKUP_SCRIPT"
        print_status "Backup script created ✓"
    fi
}

# Create monitoring configuration
create_monitoring_config() {
    PROMETHEUS_CONFIG="${SCRIPT_DIR}/monitoring/prometheus.yml"
    
    if [ ! -f "$PROMETHEUS_CONFIG" ]; then
        print_status "Creating monitoring configuration..."
        
        cat > "$PROMETHEUS_CONFIG" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'valorant-tracker-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    scrape_interval: 30s
    
  - job_name: 'flaresolverr'
    static_configs:
      - targets: ['flaresolverr:8191']
    scrape_interval: 60s

rule_files:
  # - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - alertmanager:9093
EOF
        
        print_status "Monitoring configuration created ✓"
    fi
}

# Initialize the system
initialize_system() {
    print_status "Initializing system..."
    
    # Pull all required images
    print_status "Pulling Docker images..."
    docker-compose pull
    
    # Start core services
    print_status "Starting core services..."
    docker-compose up -d postgres flaresolverr
    
    # Wait for services to be healthy
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check if services are healthy
    if docker-compose ps | grep -q "healthy"; then
        print_status "Core services started successfully ✓"
    else
        print_warning "Some services may not be fully ready yet"
    fi
    
    # Initialize database
    print_status "Initializing database..."
    docker-compose run --rm ingestion init-db
    
    # Start API service
    print_status "Starting API service..."
    docker-compose up -d app
    
    print_status "System initialization complete ✓"
}

# Show system status
show_status() {
    print_header
    print_status "System Status:"
    echo
    
    # Docker Compose status
    docker-compose ps
    echo
    
    # Service health
    print_status "Service Health Checks:"
    
    # Check FlareSolverr
    if curl -s -f http://localhost:8191/v1 > /dev/null 2>&1; then
        echo -e "  FlareSolverr: ${GREEN}✓ Running${NC}"
    else
        echo -e "  FlareSolverr: ${RED}✗ Not accessible${NC}"
    fi
    
    # Check API
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  API Server: ${GREEN}✓ Running${NC}"
    else
        echo -e "  API Server: ${RED}✗ Not accessible${NC}"
    fi
    
    # Check Database
    if docker-compose exec -T postgres pg_isready -U valorant_user > /dev/null 2>&1; then
        echo -e "  Database: ${GREEN}✓ Running${NC}"
    else
        echo -e "  Database: ${RED}✗ Not accessible${NC}"
    fi
    
    echo
    print_status "Access URLs:"
    echo "  🌐 API Dashboard: http://localhost:8000/dashboard"
    echo "  📚 API Documentation: http://localhost:8000/docs"
    echo "  🔧 FlareSolverr: http://localhost:8191"
    
    if docker-compose ps | grep -q "grafana.*Up"; then
        echo "  📊 Grafana Dashboard: http://localhost:3000"
    fi
}

# Test the system
test_system() {
    print_status "Testing system functionality..."
    
    # Test FlareSolverr
    print_status "Testing FlareSolverr connection..."
    if curl -s -X POST http://localhost:8191/v1 \
        -H "Content-Type: application/json" \
        -d '{"cmd": "sessions.list"}' | grep -q '"status":"ok"'; then
        echo -e "  FlareSolverr: ${GREEN}✓ Working${NC}"
    else
        echo -e "  FlareSolverr: ${RED}✗ Failed${NC}"
        return 1
    fi
    
    # Test API health
    print_status "Testing API health..."
    if curl -s -f http://localhost:8000/health | grep -q '"status":"healthy"'; then
        echo -e "  API Health: ${GREEN}✓ Working${NC}"
    else
        echo -e "  API Health: ${RED}✗ Failed${NC}"
        return 1
    fi
    
    # Test database connection
    print_status "Testing database connection..."
    if curl -s -f http://localhost:8000/admin/stats > /dev/null 2>&1; then
        echo -e "  Database: ${GREEN}✓ Working${NC}"
    else
        echo -e "  Database: ${RED}✗ Failed${NC}"
        return 1
    fi
    
    # Test update system
    print_status "Testing update system (this may take a moment)..."
    if curl -s -X POST http://localhost:8000/admin/test-update \
        -H "Content-Type: application/json" \
        -d '{"test_riot_id":"TenZ#tenz"}' | grep -q '"test_result"'; then
        echo -e "  Update System: ${GREEN}✓ Working${NC}"
    else
        echo -e "  Update System: ${YELLOW}⚠ Limited (may be rate limited)${NC}"
    fi
    
    print_status "System test completed ✓"
}

# Update a player (example)
update_player() {
    local RIOT_ID="$1"
    
    if [ -z "$RIOT_ID" ]; then
        print_error "Please provide a Riot ID (e.g., username#tag)"
        return 1
    fi
    
    print_status "Updating player: $RIOT_ID"
    
    curl -X POST "http://localhost:8000/players/${RIOT_ID}/update" \
        -H "Content-Type: application/json" | jq '.' || echo "Update request sent"
}

# Show logs
show_logs() {
    local SERVICE="$1"
    
    if [ -z "$SERVICE" ]; then
        print_status "Available services for logs:"
        docker-compose ps --services
        return 0
    fi
    
    print_status "Showing logs for: $SERVICE"
    docker-compose logs -f "$SERVICE"
}

# Main menu
show_help() {
    print_header
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  setup          - Initial system setup"
    echo "  start          - Start all services"
    echo "  stop           - Stop all services"
    echo "  restart        - Restart all services"
    echo "  status         - Show system status"
    echo "  test           - Test system functionality"
    echo "  logs [service] - Show logs for a service"
    echo "  update [id]    - Update a player (e.g., 'username#tag')"
    echo "  backup         - Create database backup"
    echo "  clean          - Clean up Docker resources"
    echo "  help           - Show this help message"
    echo
    echo "Examples:"
    echo "  $0 setup                    # Initial setup"
    echo "  $0 status                   # Check system status"
    echo "  $0 update 'TenZ#tenz'       # Update a player"
    echo "  $0 logs app                 # Show API logs"
    echo
}

# Main script logic
case "${1:-help}" in
    setup)
        print_header
        check_dependencies
        create_directories
        create_env_file
        create_backup_script
        create_monitoring_config
        initialize_system
        show_status
        echo
        print_status "Setup complete! 🎉"
        print_status "Visit http://localhost:8000/dashboard to get started"
        ;;
    start)
        print_status "Starting all services..."
        docker-compose up -d
        sleep 10
        show_status
        ;;
    stop)
        print_status "Stopping all services..."
        docker-compose down
        ;;
    restart)
        print_status "Restarting all services..."
        docker-compose restart
        sleep 10
        show_status
        ;;
    status)
        show_status
        ;;
    test)
        test_system
        ;;
    logs)
        show_logs "$2"
        ;;
    update)
        update_player "$2"
        ;;
    backup)
        print_status "Creating database backup..."
        docker-compose run --rm backup /usr/local/bin/backup.sh
        ;;
    clean)
        print_warning "This will remove all Docker containers, networks, and volumes."
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v --remove-orphans
            docker system prune -f
            print_status "Cleanup complete"
        fi
        ;;
    help|*)
        show_help
        ;;
esac