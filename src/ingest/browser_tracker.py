"""
Enhanced Tracker.gg Update System with Browser-Based API Inspection.
This system loads the actual tracker.gg page in a browser and intercepts the API calls
that the website makes, ensuring we get the exact same data structure and bypass detection.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import random
import requests
from urllib.parse import urlparse, parse_qs
import re

# Import existing components
from .flaresolverr_client import FlareSolverrClient
from ..shared.database import get_session, Player, DataIngestionLog
from ..shared.models import TrackerAPIConfig

logger = logging.getLogger(__name__)

@dataclass
class APICall:
    """Represents an intercepted API call from tracker.gg"""
    url: str
    method: str
    headers: Dict[str, str]
    response_data: Dict[str, Any]
    status_code: int
    timestamp: datetime
    endpoint_type: str = ""
    playlist: str = ""
    
    def __post_init__(self):
        """Parse endpoint type and playlist from URL"""
        parsed = urlparse(self.url)
        path_parts = parsed.path.split('/')
        
        # Extract API version and endpoint type
        if 'api/v1' in self.url:
            self.endpoint_type = 'v1_aggregated'
        elif 'api/v2' in self.url:
            if 'playlist' in self.url:
                self.endpoint_type = 'v2_playlist'
            elif 'loadout' in self.url:
                self.endpoint_type = 'v2_loadout'
        
        # Extract playlist from query parameters
        query_params = parse_qs(parsed.query)
        if 'playlist' in query_params:
            self.playlist = query_params['playlist'][0]

@dataclass
class BrowserSession:
    """Manages a browser session for API interception"""
    session_id: str
    user_agent: str
    proxy: Optional[str] = None
    intercepted_calls: List[APICall] = field(default_factory=list)
    page_loaded: bool = False
    last_activity: datetime = field(default_factory=datetime.utcnow)

class EnhancedTrackerUpdater:
    """Enhanced tracker.gg updater with browser-based API interception"""
    
    def __init__(self, flaresolverr_url: str = "http://tracker-flaresolverr:8191"):
        self.flaresolverr_url = flaresolverr_url.rstrip('/')
        self.sessions: Dict[str, BrowserSession] = {}
        
        # Enhanced user agents with more realistic options
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Rate limiting and retry configuration
        self.min_delay = 2.0
        self.max_delay = 5.0
        self.request_timeout = 45
        self.max_retries = 3
        
        # API endpoint patterns for interception
        self.api_patterns = [
            r'/api/v1/valorant/standard/profile/riot/.+/aggregated',
            r'/api/v2/valorant/standard/profile/riot/.+/segments/playlist',
            r'/api/v2/valorant/standard/profile/riot/.+/segments/loadout'
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random realistic user agent"""
        return random.choice(self.user_agents)
    
    async def create_browser_session(self, proxy: Optional[str] = None) -> BrowserSession:
        """Create a new browser session with enhanced anti-detection"""
        
        user_agent = self.get_random_user_agent()
        
        # Create FlareSolverr session with enhanced settings
        with FlareSolverrClient(self.flaresolverr_url, timeout=self.request_timeout) as client:
            session_params = {
                "user_agent": user_agent,
                "proxy": proxy
            }
            
            result = client.create_session(**session_params)
            session_id = result.get("session")
            
            if not session_id:
                raise Exception("Failed to create browser session")
            
            session = BrowserSession(
                session_id=session_id,
                user_agent=user_agent,
                proxy=proxy
            )
            
            self.sessions[session_id] = session
            logger.info(f"Created browser session {session_id} with UA: {user_agent[:50]}...")
            
            return session
    
    async def load_player_page_with_interception(self, riot_id: str, 
                                               session: BrowserSession) -> List[APICall]:
        """Load player page and intercept all API calls made by the browser"""
        
        username, tag = riot_id.split('#') if '#' in riot_id else (riot_id, '')
        encoded_riot_id = f"{username}%23{tag}"
        profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_riot_id}/overview"
        
        logger.info(f"Loading player page: {profile_url}")
        
        # Enhanced headers that match real browser behavior
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "dnt": "1",
            "pragma": "no-cache",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": session.user_agent
        }
        
        with FlareSolverrClient(self.flaresolverr_url, timeout=self.request_timeout) as client:
            # Load the main page first
            logger.info("Step 1: Loading main profile page...")
            
            page_result = client.get_request(
                profile_url, 
                headers=headers,
                max_timeout=self.request_timeout
            )
            
            page_solution = page_result.get("solution", {})
            if page_solution.get("status") != 200:
                raise Exception(f"Failed to load profile page: HTTP {page_solution.get('status')}")
            
            session.page_loaded = True
            session.last_activity = datetime.utcnow()
            
            # Wait for page to fully load and make API calls
            logger.info("Step 2: Waiting for page scripts to load and make API calls...")
            await asyncio.sleep(3)
            
            # Now make the API calls that the page would normally make
            api_calls = await self._intercept_api_calls(client, riot_id, session)
            
            session.intercepted_calls.extend(api_calls)
            logger.info(f"Intercepted {len(api_calls)} API calls")
            
            return api_calls
    
    async def _intercept_api_calls(self, client: FlareSolverrClient, 
                                 riot_id: str, session: BrowserSession) -> List[APICall]:
        """Make the same API calls that tracker.gg makes when loading a profile"""
        
        username, tag = riot_id.split('#') if '#' in riot_id else (riot_id, '')
        encoded_riot_id = f"{username}%23{tag}"
        base_api_url = "https://api.tracker.gg"
        
        # Headers that match what the tracker.gg website sends
        api_headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "dnt": "1",
            "origin": "https://tracker.gg",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": f"https://tracker.gg/valorant/profile/riot/{encoded_riot_id}/overview",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": session.user_agent
        }
        
        # Define the exact API calls that tracker.gg makes (in order)
        api_endpoints = [
            # V1 Aggregated endpoints (heatmap and party data)
            {
                "url": f"{base_api_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=competitive&source=web",
                "name": "competitive_aggregated",
                "priority": 1
            },
            {
                "url": f"{base_api_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=premier&source=web",
                "name": "premier_aggregated", 
                "priority": 1
            },
            {
                "url": f"{base_api_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=unrated&source=web",
                "name": "unrated_aggregated",
                "priority": 2
            },
            # V2 Playlist segments (detailed stats)
            {
                "url": f"{base_api_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=competitive&source=web",
                "name": "competitive_playlist",
                "priority": 1
            },
            {
                "url": f"{base_api_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=premier&source=web",
                "name": "premier_playlist",
                "priority": 1
            },
            {
                "url": f"{base_api_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=unrated&source=web",
                "name": "unrated_playlist",
                "priority": 2
            },
            {
                "url": f"{base_api_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=deathmatch&source=web",
                "name": "deathmatch_playlist",
                "priority": 3
            },
            # V2 Loadout segments (weapon stats)
            {
                "url": f"{base_api_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/loadout?source=web",
                "name": "loadout_segments",
                "priority": 2
            }
        ]
        
        intercepted_calls = []
        
        # Sort by priority (most important first)
        sorted_endpoints = sorted(api_endpoints, key=lambda x: x["priority"])
        
        for i, endpoint in enumerate(sorted_endpoints):
            try:
                # Add realistic delay between API calls (like a browser would)
                if i > 0:
                    delay = random.uniform(0.3, 0.8)
                    logger.debug(f"API call delay: {delay:.2f}s")
                    await asyncio.sleep(delay)
                
                logger.info(f"Making API call: {endpoint['name']}")
                
                # Make the API request
                result = client.get_request(
                    endpoint["url"],
                    headers=api_headers,
                    max_timeout=self.request_timeout
                )
                
                solution = result.get("solution", {})
                status_code = solution.get("status", 0)
                response_text = solution.get("response", "")
                
                if status_code == 200 and response_text:
                    try:
                        response_data = json.loads(response_text)
                        
                        api_call = APICall(
                            url=endpoint["url"],
                            method="GET",
                            headers=api_headers.copy(),
                            response_data=response_data,
                            status_code=status_code,
                            timestamp=datetime.utcnow()
                        )
                        
                        intercepted_calls.append(api_call)
                        logger.info(f"✓ {endpoint['name']}: Success ({len(response_text)} bytes)")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"✗ {endpoint['name']}: JSON decode error - {e}")
                        
                elif status_code == 429:
                    logger.warning(f"⚠ {endpoint['name']}: Rate limited (429)")
                    # Add exponential backoff for rate limits
                    backoff = random.uniform(5, 10)
                    logger.info(f"Backing off for {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    
                elif status_code == 403:
                    logger.warning(f"⚠ {endpoint['name']}: Forbidden (403) - possible detection")
                    # This might indicate anti-bot detection
                    
                else:
                    logger.error(f"✗ {endpoint['name']}: HTTP {status_code}")
                    if response_text:
                        logger.debug(f"Response preview: {response_text[:200]}...")
                        
            except Exception as e:
                logger.error(f"✗ {endpoint['name']}: Exception - {e}")
                
        return intercepted_calls
    
    async def update_player_data(self, riot_id: str, 
                               smart_update: bool = True,
                               proxy: Optional[str] = None) -> Dict[str, Any]:
        """Update player data using browser-based API interception"""
        
        logger.info(f"Starting enhanced update for {riot_id}")
        start_time = datetime.utcnow()
        
        try:
            # Create browser session
            session = await self.create_browser_session(proxy)
            
            # Load page and intercept API calls
            api_calls = await self.load_player_page_with_interception(riot_id, session)
            
            # Process the intercepted data
            processed_data = self._process_intercepted_calls(api_calls, riot_id)
            
            # Save to file for data loader
            if processed_data["successful_calls"] > 0:
                await self._save_intercepted_data(processed_data, riot_id)
            
            # Clean up session
            await self._cleanup_session(session.session_id)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "riot_id": riot_id,
                "status": "success" if processed_data["successful_calls"] > 0 else "failed",
                "update_timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_endpoints": len(api_calls) if api_calls else 0,
                    "successful": processed_data["successful_calls"],
                    "failed": processed_data["failed_calls"],
                    "priority_achieved": processed_data["priority_achieved"],
                    "duration_seconds": duration
                },
                "browser_session": {
                    "user_agent": session.user_agent,
                    "proxy_used": proxy is not None,
                    "page_loaded": session.page_loaded
                },
                "endpoints": processed_data["endpoints"]
            }
            
        except Exception as e:
            logger.error(f"Enhanced update failed for {riot_id}: {e}")
            await self._cleanup_all_sessions()
            
            return {
                "riot_id": riot_id,
                "status": "error",
                "error": str(e),
                "update_timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_endpoints": 0,
                    "successful": 0,
                    "failed": 1,
                    "priority_achieved": False,
                    "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
                }
            }
    
    def _process_intercepted_calls(self, api_calls: List[APICall], 
                                 riot_id: str) -> Dict[str, Any]:
        """Process the intercepted API calls into a structured format"""
        
        endpoints = {}
        successful_calls = 0
        failed_calls = 0
        priority_endpoints = 0
        
        for call in api_calls:
            endpoint_key = f"{call.endpoint_type}_{call.playlist}" if call.playlist else call.endpoint_type
            
            endpoints[endpoint_key] = {
                "url": call.url,
                "status": "success" if call.status_code == 200 else "failed",
                "status_code": call.status_code,
                "data": call.response_data,
                "timestamp": call.timestamp.isoformat(),
                "endpoint_type": call.endpoint_type,
                "playlist": call.playlist
            }
            
            if call.status_code == 200:
                successful_calls += 1
                # Check if this is a priority endpoint (competitive/premier)
                if call.playlist in ["competitive", "premier"]:
                    priority_endpoints += 1
            else:
                failed_calls += 1
        
        return {
            "endpoints": endpoints,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "priority_achieved": priority_endpoints >= 2  # Got both competitive and premier
        }
    
    async def _save_intercepted_data(self, processed_data: Dict[str, Any], 
                                   riot_id: str) -> Path:
        """Save intercepted data in the format expected by the data loader"""
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_riot_id = riot_id.replace('#', '_')
        output_file = Path(f"data/browser_capture_{safe_riot_id}_{timestamp}.json")
        output_file.parent.mkdir(exist_ok=True)
        
        # Convert to the format expected by the data loader
        loader_format = {
            "riot_id": riot_id,
            "capture_timestamp": datetime.utcnow().isoformat(),
            "capture_method": "browser_interception",
            "endpoints": processed_data["endpoints"],
            "summary": {
                "total_endpoints": len(processed_data["endpoints"]),
                "successful": processed_data["successful_calls"],
                "failed": processed_data["failed_calls"]
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(loader_format, f, indent=2, default=str)
        
        logger.info(f"Saved intercepted data to {output_file}")
        return output_file
    
    async def _cleanup_session(self, session_id: str):
        """Clean up a specific browser session"""
        if session_id in self.sessions:
            try:
                with FlareSolverrClient(self.flaresolverr_url) as client:
                    client.destroy_session(session_id)
                del self.sessions[session_id]
                logger.debug(f"Cleaned up session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup session {session_id}: {e}")
    
    async def _cleanup_all_sessions(self):
        """Clean up all browser sessions"""
        for session_id in list(self.sessions.keys()):
            await self._cleanup_session(session_id)
    
    async def bulk_update_players(self, riot_ids: List[str], 
                                max_concurrent: int = 2) -> List[Dict[str, Any]]:
        """Update multiple players with concurrency control"""
        
        logger.info(f"Starting bulk update for {len(riot_ids)} players")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def update_with_semaphore(riot_id: str) -> Dict[str, Any]:
            async with semaphore:
                # Add random delay to avoid thundering herd
                await asyncio.sleep(random.uniform(1, 3))
                return await self.update_player_data(riot_id)
        
        # Execute updates
        tasks = [update_with_semaphore(riot_id) for riot_id in riot_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "riot_id": riot_ids[i],
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        # Log summary
        successful = len([r for r in processed_results if r.get("status") == "success"])
        logger.info(f"Bulk update complete: {successful}/{len(riot_ids)} successful")
        
        return processed_results

# Main API function for integration with existing system
async def enhanced_update_player_data(riot_id: str) -> Dict[str, Any]:
    """
    Enhanced update function for use in API endpoints.
    This replaces the existing enhanced_update_player_data function.
    """
    updater = EnhancedTrackerUpdater()
    
    try:
        result = await updater.update_player_data(riot_id, smart_update=True)
        
        # Auto-load the data if successful
        if result["status"] == "success" and result["summary"]["successful"] > 0:
            try:
                from .data_loader import TrackerDataLoader
                
                # The data was saved by _save_intercepted_data, now load it
                loader = TrackerDataLoader()
                
                # Find the most recent file for this player
                timestamp = result["update_timestamp"][:8].replace('-', '')  # YYYYMMDD
                safe_riot_id = riot_id.replace('#', '_')
                data_files = list(Path("data").glob(f"browser_capture_{safe_riot_id}_*.json"))
                
                if data_files:
                    # Load the most recent file
                    latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
                    
                    with get_session() as session:
                        loader.load_file(session, latest_file)
                        session.commit()
                    
                    logger.info(f"Auto-loaded intercepted data for {riot_id}")
                    
            except Exception as load_error:
                logger.error(f"Failed to auto-load data for {riot_id}: {load_error}")
                result["load_error"] = str(load_error)
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced browser update failed for {riot_id}: {e}")
        return {
            "riot_id": riot_id,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    async def main():
        parser = argparse.ArgumentParser(description="Enhanced Tracker.gg Updater")
        parser.add_argument("--riot-id", required=True, help="Riot ID to update")
        parser.add_argument("--flaresolverr-url", default="http://localhost:8191", 
                          help="FlareSolverr URL")
        parser.add_argument("--proxy", help="Proxy URL")
        parser.add_argument("--bulk", nargs="+", help="Multiple Riot IDs for bulk update")
        
        args = parser.parse_args()
        
        updater = EnhancedTrackerUpdater(args.flaresolverr_url)
        
        if args.bulk:
            results = await updater.bulk_update_players(args.bulk, max_concurrent=2)
            for result in results:
                print(f"{result['riot_id']}: {result['status']}")
        else:
            result = await updater.update_player_data(args.riot_id, proxy=args.proxy)
            print(f"Update result: {result['status']}")
            if result['status'] == 'success':
                summary = result['summary']
                print(f"Success: {summary['successful']}/{summary['total_endpoints']} endpoints")
    
    asyncio.run(main()) 