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
    import asyncio
    from .ingest.data_loader import load_data_from_directory, load_single_file, init_db
    from .ingest.user_manager import user_manager
    from .ingest.startup_initializer import initialize_all_users_at_startup
    
    if args.init_db:
        init_db()
        print("✓ Database initialized successfully!")
        return
    
    if args.init_all_users:
        print("🚀 Initializing all tracked users...")
        
        async def run_init():
            max_concurrent = args.max_concurrent or 2
            print(f"Max concurrent operations: {max_concurrent}")
            
            results = await initialize_all_users_at_startup(max_concurrent)
            
            if results:
                successful = len([r for r in results.values() if r.get("status") != "error"])
                failed = len(results) - successful
                print(f"✓ Initialization completed: {successful} successful, {failed} failed")
                
                # Show detailed results
                for riot_id, result in results.items():
                    if result.get("status") == "error":
                        print(f"  ❌ {riot_id}: {result.get('error', 'Unknown error')}")
                    else:
                        duration = result.get("duration_minutes", 0)
                        endpoints = result.get("successful_endpoints", 0)
                        print(f"  ✅ {riot_id}: {endpoints} endpoints loaded in {duration:.1f} minutes")
            else:
                print("⚠️  No users configured for initialization")
        
        asyncio.run(run_init())
        return
    
    if args.list_users:
        users = user_manager.get_tracked_users()
        print(f"📋 Tracked users ({len(users)}):")
        for user in users:
            print(f"  • {user}")
        return
    
    if args.add_user:
        if user_manager.add_user(args.add_user):
            print(f"✓ Added user: {args.add_user}")
        else:
            print(f"⚠️  User {args.add_user} already tracked or failed to add")
        return
    
    if args.remove_user:
        if user_manager.remove_user(args.remove_user):
            print(f"✓ Removed user: {args.remove_user}")
        else:
            print(f"⚠️  User {args.remove_user} not found or failed to remove")
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
  
  # User management
  python -m src ingest --list-users
  python -m src ingest --add-user "TenZ#tenz"
  python -m src ingest --init-all-users --max-concurrent 2
  
  
  # Load data from files
  python -m src ingest --load-directory "./data"
  python -m src ingest --load-file "capture_appoloZ_sun_123456.json"
  
  # Start API server
  python -m src api
  python -m src api --port 8080 --reload
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Ingestion subcommand
    ingest_parser = subparsers.add_parser('ingest', help='Data ingestion operations')
    ingest_parser.add_argument('--init-db', action='store_true', help='Initialize database')
    ingest_parser.add_argument('--init-all-users', action='store_true', help='Initialize all tracked users (startup mode)')
    ingest_parser.add_argument('--max-concurrent', type=int, default=2, help='Max concurrent user initializations')
    ingest_parser.add_argument('--list-users', action='store_true', help='List all tracked users')
    ingest_parser.add_argument('--add-user', help='Add a user to tracking list (username#tag)')
    ingest_parser.add_argument('--remove-user', help='Remove a user from tracking list (username#tag)')
    ingest_parser.add_argument('--load-file', help='Load a single JSON file')
    ingest_parser.add_argument('--load-directory', help='Load all JSON files from directory')
    
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