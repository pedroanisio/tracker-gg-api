"""
Main entry point for the Tracker.gg Valorant API system.
Provides commands for data ingestion and API serving.
"""

import argparse
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_ingestion(args):
    """Run data ingestion operations."""
    from .ingest.data_loader import load_data_from_directory, load_single_file, init_db
    from .ingest.flaresolverr_client import test_flaresolverr_connection, capture_player_data
    from .ingest.scraper import scrape_player, test_scraper_connection
    
    if args.init_db:
        init_db()
        print("✓ Database initialized successfully!")
        return
    
    if args.test_flaresolverr:
        success = test_flaresolverr_connection(args.flaresolverr_url)
        print(f"FlareSolverr test: {'✓ Success' if success else '✗ Failed'}")
        return
    
    if args.test_scraper:
        success = test_scraper_connection(args.flaresolverr_url)
        print(f"Scraper test: {'✓ Success' if success else '✗ Failed'}")
        return
    
    if args.scrape_player:
        print(f"Scraping player: {args.scrape_player}")
        data = scrape_player(
            args.scrape_player, 
            args.flaresolverr_url,
            args.output_file
        )
        if data.get("status") == "success":
            print("✓ Scraping completed successfully!")
            if "api_data" in data and "summary" in data["api_data"]:
                summary = data["api_data"]["summary"]
                print(f"API Success rate: {summary['successful']}/{summary['total_endpoints']}")
        else:
            print(f"✗ Scraping failed: {data.get('error', 'Unknown error')}")
        return
    
    if args.capture_player:
        print(f"Capturing API data for player: {args.capture_player}")
        data = capture_player_data(
            args.capture_player,
            args.flaresolverr_url,
            args.output_file
        )
        summary = data.get("summary", {})
        print(f"✓ Capture completed: {summary.get('successful', 0)}/{summary.get('total_endpoints', 0)} endpoints")
        return
    
    if args.load_file:
        print(f"Loading file: {args.load_file}")
        stats = load_single_file(args.load_file)
        print(f"✓ File loaded: {stats}")
        return
    
    if args.load_directory:
        print(f"Loading directory: {args.load_directory}")
        stats = load_data_from_directory(args.load_directory)
        print(f"✓ Directory loaded: {stats}")
        return
    
    print("No ingestion operation specified. Use --help to see available options.")


def run_api(args):
    """Run the API server."""
    import uvicorn
    from .expose.api import app
    
    print(f"Starting API server on {args.host}:{args.port}")
    print(f"API documentation will be available at http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level.lower()
    )


def main():
    """Main entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="Tracker.gg Valorant API System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize database
  python -m src ingest --init-db
  
  # Test connections
  python -m src ingest --test-flaresolverr
  python -m src ingest --test-scraper
  
  # Scrape a player
  python -m src ingest --scrape-player "apolloZ#sun" --output-file "apolloZ_data.json"
  
  # Load data from files
  python -m src ingest --load-directory "./data"
  python -m src ingest --load-file "capture_apolloZ_sun_123456.json"
  
  # Start API server
  python -m src api
  python -m src api --port 8080 --reload
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Ingestion subcommand
    ingest_parser = subparsers.add_parser('ingest', help='Data ingestion operations')
    ingest_parser.add_argument('--init-db', action='store_true', help='Initialize database')
    ingest_parser.add_argument('--test-flaresolverr', action='store_true', help='Test FlareSolverr connection')
    ingest_parser.add_argument('--test-scraper', action='store_true', help='Test scraper connection')
    ingest_parser.add_argument('--scrape-player', help='Scrape a specific player (username#tag)')
    ingest_parser.add_argument('--capture-player', help='Capture API data for a player (username#tag)')
    ingest_parser.add_argument('--load-file', help='Load a single JSON file')
    ingest_parser.add_argument('--load-directory', help='Load all JSON files from directory')
    ingest_parser.add_argument('--flaresolverr-url', default='http://localhost:8191', help='FlareSolverr URL')
    ingest_parser.add_argument('--output-file', help='Output file for scraped/captured data')
    
    # API subcommand
    api_parser = subparsers.add_parser('api', help='Start API server')
    api_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    api_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    api_parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    api_parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'ingest':
        run_ingestion(args)
    elif args.command == 'api':
        run_api(args)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main() 