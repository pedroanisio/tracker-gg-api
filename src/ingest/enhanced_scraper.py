"""
Enhanced Valorant Scraper for Tracker.gg
Unified scraper combining web scraping, API capture, and anti-detection techniques.
"""

import asyncio
import random
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urljoin
from sqlmodel import Session, select
from bs4 import BeautifulSoup

from .flaresolverr_client import FlareSolverrClient
from ..shared.database import get_session, Player, DataIngestionLog
from ..shared.utils import (
    setup_logger, parse_riot_id, encode_riot_id, get_current_timestamp,
    get_current_datetime, get_random_user_agent, get_browser_headers,
    get_api_headers, TRACKER_API_BASE_URL, TRACKER_WEB_BASE_URL,
    create_success_response, create_error_response
)

logger = setup_logger(__name__)

@dataclass
class UpdateCheckpoint:
    """Checkpoint for tracking update progress."""
    player_id: str
    last_update: datetime
    endpoints_fetched: Set[str]
    priority_score: float
    retry_count: int = 0

class EnhancedValorantScraper:
    """Enhanced scraper with web scraping, API capture, and anti-detection."""
    
    def __init__(self, 
                 flaresolverr_url: str = "http://tracker-flaresolverr:8191",
                 use_proxy_rotation: bool = False,
                 proxy_list: Optional[List[str]] = None):
        """
        Initialize enhanced scraper.
        
        Args:
            flaresolverr_url: FlareSolverr service URL
            use_proxy_rotation: Whether to rotate proxies
            proxy_list: List of proxy URLs
        """
        self.flaresolverr_url = flaresolverr_url
        self.use_proxy_rotation = use_proxy_rotation
        self.proxy_list = proxy_list or []
        self.proxy_index = 0
        
        # Request timing settings
        self.min_delay = 1.0
        self.max_delay = 3.0
        self.backoff_multiplier = 2.0
        self.max_retries = 3
        
        # Checkpoints for tracking updates
        self.checkpoints: Dict[str, UpdateCheckpoint] = {}
        
        # Priority endpoints (most important data first)
        self.endpoint_priorities = {
            "v1_competitive_aggregated": 1.0,
            "v1_premier_aggregated": 0.9,
            "v2_competitive_playlist": 0.8,
            "v2_premier_playlist": 0.7,
            "v1_unrated_aggregated": 0.6,
            "v2_unrated_playlist": 0.5,
            "v2_deathmatch_playlist": 0.4,
            "v2_loadout_segments": 0.3
        }
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy in rotation."""
        if not self.use_proxy_rotation or not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    async def smart_delay(self, retry_count: int = 0) -> None:
        """Implement smart delay with jitter and exponential backoff."""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        
        # Add exponential backoff for retries
        if retry_count > 0:
            base_delay *= (self.backoff_multiplier ** retry_count)
        
        # Add random jitter (±20%)
        jitter = base_delay * 0.2 * (random.random() * 2 - 1)
        final_delay = max(0.5, base_delay + jitter)
        
        logger.debug(f"Delaying {final_delay:.2f}s (retry: {retry_count})")
        await asyncio.sleep(final_delay)
    
    def should_update_player(self, player: Player) -> bool:
        """
        Determine if a player's data should be updated based on freshness.
        
        Args:
            player: Player object
            
        Returns:
            True if update needed, False otherwise
        """
        # Always update if never updated
        if not player.last_updated:
            return True
        
        # Calculate time since last update
        time_since_update = get_current_datetime() - player.last_updated
        
        # Priority scoring based on various factors
        priority_score = 0.0
        
        # Age factor (older data = higher priority)
        hours_old = time_since_update.total_seconds() / 3600
        if hours_old > 24:  # More than 1 day old
            priority_score += 1.0
        elif hours_old > 12:  # More than 12 hours old
            priority_score += 0.7
        elif hours_old > 6:  # More than 6 hours old
            priority_score += 0.5
        elif hours_old > 2:  # More than 2 hours old
            priority_score += 0.3
        
        # Add randomness to avoid predictable patterns
        priority_score += random.uniform(0, 0.2)
        
        # Update if priority score is high enough
        return priority_score >= 0.5
    
    def get_player_profile_page(self, riot_id: str) -> Optional[str]:
        """
        Get the HTML content of a player's profile page.
        
        Args:
            riot_id: Player's Riot ID (username#tag)
            
        Returns:
            HTML content or None if failed
        """
        
        encoded_riot_id = encode_riot_id(riot_id)
        profile_url = f"{TRACKER_WEB_BASE_URL}/valorant/profile/riot/{encoded_riot_id}/overview"
        
        try:
            with FlareSolverrClient(self.flaresolverr_url) as client:
                headers = get_browser_headers(riot_id)
                result = client.get_request(profile_url, headers=headers)
                
                solution = result.get("solution", {})
                if solution.get("status") == 200:
                    return solution.get("response", "")
                else:
                    logger.error(f"Failed to get profile page: HTTP {solution.get('status')}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting profile page: {e}")
            return None
    
    def parse_player_overview(self, html_content: str) -> Dict[str, Any]:
        """
        Parse player overview data from HTML.
        
        Args:
            html_content: HTML content from profile page
            
        Returns:
            Parsed player data
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize result
        player_data = {
            "basic_info": {},
            "current_rank": {},
            "peak_rank": {},
            "overview_stats": {},
            "recent_matches": []
        }
        
        try:
            # Extract basic player info
            player_name_elem = soup.find('span', class_='trn-ign__username')
            if player_name_elem:
                player_data["basic_info"]["username"] = player_name_elem.text.strip()
            
            player_tag_elem = soup.find('span', class_='trn-ign__discriminator')
            if player_tag_elem:
                player_data["basic_info"]["tag"] = player_tag_elem.text.strip().replace('#', '')
            
            # Extract current rank
            rank_elem = soup.find('div', class_='valorant-ranked-badge')
            if rank_elem:
                rank_img = rank_elem.find('img')
                if rank_img and 'alt' in rank_img.attrs:
                    player_data["current_rank"]["tier"] = rank_img['alt']
                
                rank_text = rank_elem.find('div', class_='valorant-ranked-badge__rank-text')
                if rank_text:
                    player_data["current_rank"]["rank_text"] = rank_text.text.strip()
            
            # Extract overview statistics
            stat_cards = soup.find_all('div', class_='numbers__number-value')
            stat_labels = soup.find_all('div', class_='numbers__number-label')
            
            for stat_card, stat_label in zip(stat_cards, stat_labels):
                if stat_card and stat_label:
                    label = stat_label.text.strip()
                    value = stat_card.text.strip()
                    player_data["overview_stats"][label] = value
            
            # Extract recent matches (basic info)
            match_cards = soup.find_all('div', class_='match')
            for match_card in match_cards[:5]:  # Last 5 matches
                match_info = {}
                
                # Map name
                map_elem = match_card.find('div', class_='match__map')
                if map_elem:
                    match_info["map"] = map_elem.text.strip()
                
                # Score
                score_elem = match_card.find('div', class_='match__score')
                if score_elem:
                    match_info["score"] = score_elem.text.strip()
                
                # Result (win/loss)
                if 'match--won' in match_card.get('class', []):
                    match_info["result"] = "win"
                elif 'match--lost' in match_card.get('class', []):
                    match_info["result"] = "loss"
                else:
                    match_info["result"] = "unknown"
                
                player_data["recent_matches"].append(match_info)
            
        except Exception as e:
            logger.error(f"Error parsing player overview: {e}")
        
        return player_data
    
    def create_checkpoint(self, player_id: str, last_update: datetime) -> UpdateCheckpoint:
        """Create or update checkpoint for a player."""
        if player_id in self.checkpoints:
            checkpoint = self.checkpoints[player_id]
            checkpoint.last_update = last_update
            checkpoint.retry_count = 0
        else:
            checkpoint = UpdateCheckpoint(
                player_id=player_id,
                last_update=last_update,
                endpoints_fetched=set(),
                priority_score=1.0,
                retry_count=0
            )
            self.checkpoints[player_id] = checkpoint
        
        return checkpoint
    
    async def fetch_endpoint_with_retry(self, 
                                      client: FlareSolverrClient,
                                      endpoint_name: str, 
                                      url: str, 
                                      headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Fetch single endpoint with retry logic and anti-detection measures.
        
        Args:
            client: FlareSolverr client
            endpoint_name: Name of the endpoint
            url: URL to fetch
            headers: Request headers
            
        Returns:
            Endpoint result
        """
        for attempt in range(self.max_retries):
            try:
                # Apply anti-detection delay
                if attempt > 0:
                    await self.smart_delay(attempt)
                
                # Randomize headers for each attempt
                attempt_headers = headers.copy()
                attempt_headers["user-agent"] = get_random_user_agent()
                
                logger.info(f"Fetching {endpoint_name} (attempt {attempt + 1}/{self.max_retries})")
                
                result = client.get_request(url, headers=attempt_headers)
                solution = result.get("solution", {})
                status_code = solution.get("status", 0)
                response_text = solution.get("response", "")
                
                # Success case
                if status_code == 200 and response_text:
                    try:
                        api_data = json.loads(response_text)
                        logger.info(f"✓ {endpoint_name}: Success")
                        return {
                            "url": url,
                            "status": "success",
                            "status_code": status_code,
                            "data": api_data,
                            "timestamp": get_current_timestamp()
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"✗ {endpoint_name}: JSON decode error - {e}")
                        if attempt == self.max_retries - 1:  # Last attempt
                            return {
                                "url": url,
                                "status": "json_error",
                                "status_code": status_code,
                                "error": str(e),
                                "raw_response": response_text[:500]
                            }
                
                # Rate limited or blocked
                elif status_code == 429 or status_code == 403:
                    logger.warning(f"⚠ {endpoint_name}: Rate limited/blocked (HTTP {status_code})")
                    # Longer delay for rate limiting
                    await self.smart_delay(attempt + 2)
                    continue
                
                # Other HTTP errors
                else:
                    logger.error(f"✗ {endpoint_name}: HTTP {status_code}")
                    if attempt == self.max_retries - 1:  # Last attempt
                        return {
                            "url": url,
                            "status": "http_error",
                            "status_code": status_code,
                            "raw_response": response_text[:500] if response_text else "No response"
                        }
            
            except Exception as e:
                logger.error(f"✗ {endpoint_name}: Exception on attempt {attempt + 1} - {e}")
                if attempt == self.max_retries - 1:  # Last attempt
                    return {
                        "url": url,
                        "status": "error",
                        "error": str(e),
                        "attempt": attempt + 1
                    }
                
                # Wait before retry
                await self.smart_delay(attempt + 1)
        
        # Should not reach here, but just in case
        return {
            "url": url,
            "status": "max_retries_exceeded",
            "attempts": self.max_retries
        }
    
    def get_player_api_data(self, riot_id: str) -> Dict[str, Any]:
        """
        Get comprehensive player data using API capture.
        
        Args:
            riot_id: Player's Riot ID (username#tag)
            
        Returns:
            Complete API data capture
        """
        
        try:
            with FlareSolverrClient(self.flaresolverr_url) as client:
                return client.capture_tracker_api(riot_id)
        except Exception as e:
            logger.error(f"Error capturing API data: {e}")
            return create_error_response(riot_id, str(e))
    
    async def smart_update_player(self, riot_id: str, 
                                checkpoint_only_recent: bool = True) -> Dict[str, Any]:
        """
        Smart update player data with checkpointing and prioritization.
        
        Args:
            riot_id: Player's Riot ID
            checkpoint_only_recent: Only fetch recent/changed data
            
        Returns:
            Update result
        """
        encoded_riot_id = encode_riot_id(riot_id)
        
        # Create or get checkpoint
        checkpoint = self.create_checkpoint(riot_id, get_current_datetime())
        
        # Enhanced headers with anti-detection
        headers = get_api_headers(riot_id)
        
        # Define endpoints with priorities
        all_endpoints = {
            "v1_competitive_aggregated": f"{TRACKER_API_BASE_URL}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=competitive&source=web",
            "v1_premier_aggregated": f"{TRACKER_API_BASE_URL}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=premier&source=web",
            "v1_unrated_aggregated": f"{TRACKER_API_BASE_URL}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=unrated&source=web",
            "v2_competitive_playlist": f"{TRACKER_API_BASE_URL}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=competitive&source=web",
            "v2_premier_playlist": f"{TRACKER_API_BASE_URL}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=premier&source=web",
            "v2_unrated_playlist": f"{TRACKER_API_BASE_URL}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=unrated&source=web",
            "v2_deathmatch_playlist": f"{TRACKER_API_BASE_URL}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=deathmatch&source=web",
            "v2_loadout_segments": f"{TRACKER_API_BASE_URL}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/loadout?source=web"
        }
        
        # Filter endpoints based on checkpoint and priority
        if checkpoint_only_recent and checkpoint.endpoints_fetched:
            # Only fetch high-priority endpoints that weren't recently fetched
            endpoints_to_fetch = {
                name: url for name, url in all_endpoints.items()
                if (self.endpoint_priorities.get(name, 0.5) > 0.6 and 
                    name not in checkpoint.endpoints_fetched)
            }
            logger.info(f"Checkpoint mode: Fetching {len(endpoints_to_fetch)} priority endpoints")
        else:
            endpoints_to_fetch = all_endpoints
            logger.info(f"Full update: Fetching all {len(endpoints_to_fetch)} endpoints")
        
        # Sort endpoints by priority (highest first)
        sorted_endpoints = sorted(
            endpoints_to_fetch.items(),
            key=lambda x: self.endpoint_priorities.get(x[0], 0.5),
            reverse=True
        )
        
        results = {}
        successful_fetches = 0
        
        # Get proxy for this session
        proxy = self.get_next_proxy()
        
        # Create FlareSolverr session with anti-detection settings
        with FlareSolverrClient(self.flaresolverr_url) as client:
            # Create session with random user agent and optional proxy
            session_params = {
                "user_agent": get_random_user_agent()
            }
            if proxy:
                session_params["proxy"] = proxy
                logger.info(f"Using proxy: {proxy}")
            
            client.create_session(**session_params)
            
            # Fetch endpoints in priority order
            for endpoint_name, url in sorted_endpoints:
                try:
                    # Random delay between endpoints (human-like behavior)
                    if results:  # Skip delay for first request
                        await self.smart_delay()
                    
                    result = await self.fetch_endpoint_with_retry(
                        client, endpoint_name, url, headers
                    )
                    
                    results[endpoint_name] = result
                    
                    # Track successful fetches
                    if result.get("status") == "success":
                        successful_fetches += 1
                        checkpoint.endpoints_fetched.add(endpoint_name)
                    
                    # Early termination if we have critical data
                    if (checkpoint_only_recent and 
                        successful_fetches >= 3 and 
                        "v1_competitive_aggregated" in checkpoint.endpoints_fetched):
                        logger.info("Early termination: Got critical data")
                        break
                
                except Exception as e:
                    logger.error(f"Error processing {endpoint_name}: {e}")
                    results[endpoint_name] = {
                        "url": url,
                        "status": "error",
                        "error": str(e)
                    }
        
        # Update checkpoint
        checkpoint.last_update = get_current_datetime()
        if successful_fetches == 0:
            checkpoint.retry_count += 1
        else:
            checkpoint.retry_count = 0
        
        return {
            "riot_id": riot_id,
            "update_timestamp": get_current_timestamp(),
            "checkpoint_mode": checkpoint_only_recent,
            "endpoints": results,
            "summary": {
                "total_endpoints": len(endpoints_to_fetch),
                "successful": successful_fetches,
                "failed": len(endpoints_to_fetch) - successful_fetches,
                "checkpoint_status": "updated" if successful_fetches > 0 else "failed",
                "priority_achieved": successful_fetches >= 2
            },
            "anti_detection": {
                "proxy_used": proxy is not None,
                "user_agent_rotated": True,
                "delays_applied": True,
                "retry_count": checkpoint.retry_count
            }
        }
    
    def get_complete_player_data(self, riot_id: str) -> Dict[str, Any]:
        """
        Get complete player data including both web scraping and API data.
        
        Args:
            riot_id: Player's Riot ID (username#tag)
            
        Returns:
            Combined player data
        """
        
        result = create_success_response(riot_id, {
            "scraping_timestamp": time.time(),
            "web_data": {},
            "api_data": {}
        })
        
        try:
            # Get web scraping data
            logger.info(f"Scraping web data for {riot_id}")
            html_content = self.get_player_profile_page(riot_id)
            if html_content:
                result["web_data"] = self.parse_player_overview(html_content)
            else:
                result["web_data"] = {"error": "Failed to get profile page"}
            
            # Get API data
            logger.info(f"Capturing API data for {riot_id}")
            result["api_data"] = self.get_player_api_data(riot_id)
            
        except Exception as e:
            return create_error_response(riot_id, str(e))
        
        return result
    
    async def bulk_smart_update(self, 
                              riot_ids: List[str], 
                              max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """
        Perform bulk smart updates with concurrency control.
        
        Args:
            riot_ids: List of Riot IDs to update
            max_concurrent: Maximum concurrent updates
            
        Returns:
            List of update results
        """
        # Check which players actually need updates
        players_to_update = []
        
        with get_session() as session:
            for riot_id in riot_ids:
                stmt = select(Player).where(Player.riot_id == riot_id)
                player = session.exec(stmt).first()
                
                if not player or self.should_update_player(player):
                    players_to_update.append(riot_id)
        
        logger.info(f"Smart bulk update: {len(players_to_update)}/{len(riot_ids)} players need updates")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def update_with_semaphore(riot_id: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.smart_update_player(riot_id, checkpoint_only_recent=True)
        
        # Execute updates with controlled concurrency
        tasks = [update_with_semaphore(riot_id) for riot_id in players_to_update]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    create_error_response(players_to_update[i], str(result))
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    def test_connection(self) -> bool:
        """
        Test if the scraper can connect to tracker.gg.
        
        Returns:
            True if connection successful, False otherwise
        """
        
        try:
            with FlareSolverrClient(self.flaresolverr_url) as client:
                result = client.get_request(TRACKER_WEB_BASE_URL)
                solution = result.get("solution", {})
                return solution.get("status") == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Convenience functions for backward compatibility
def scrape_player(riot_id: str, 
                 flaresolverr_url: str = "http://localhost:8191",
                 output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to scrape a single player.
    
    Args:
        riot_id: Player's Riot ID
        flaresolverr_url: FlareSolverr service URL
        output_file: Optional file to save results
        
    Returns:
        Player data
    """
    
    scraper = EnhancedValorantScraper(flaresolverr_url)
    data = scraper.get_complete_player_data(riot_id)
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved data to {output_file}")
    
    return data


def test_scraper_connection(flaresolverr_url: str = "http://localhost:8191") -> bool:
    """
    Test scraper connection.
    
    Args:
        flaresolverr_url: FlareSolverr service URL
        
    Returns:
        True if successful, False otherwise
    """
    
    scraper = EnhancedValorantScraper(flaresolverr_url)
    return scraper.test_connection()


async def enhanced_update_player_data(riot_id: str) -> Dict[str, Any]:
    """
    Enhanced update function for use in API endpoints.
    
    Args:
        riot_id: Player's Riot ID
        
    Returns:
        Update result
    """
    scraper = EnhancedValorantScraper()
    
    try:
        result = await scraper.smart_update_player(riot_id, checkpoint_only_recent=True)
        
        # Save successful data to files for processing
        if result["summary"]["successful"] > 0:
            timestamp = get_current_datetime().strftime("%Y%m%d_%H%M%S")
            output_file = Path(f"data/enhanced_update_{riot_id.replace('#', '_')}_{timestamp}.json")
            output_file.parent.mkdir(exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Enhanced update data saved to {output_file}")
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced update failed for {riot_id}: {e}")
        return create_error_response(riot_id, str(e))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Valorant tracker.gg scraper")
    parser.add_argument("--riot-id", help="Riot ID to scrape (e.g., 'player#1234')")
    parser.add_argument("--flaresolverr-url", default="http://localhost:8191", help="FlareSolverr URL")
    parser.add_argument("--output", help="Output file for scraped data")
    parser.add_argument("--test-connection", action="store_true", help="Test connection only")
    parser.add_argument("--api-only", action="store_true", help="Only capture API data")
    parser.add_argument("--web-only", action="store_true", help="Only scrape web data")
    parser.add_argument("--smart-update", action="store_true", help="Use smart update with anti-detection")
    parser.add_argument("--bulk", nargs="+", help="Multiple Riot IDs for bulk update")
    
    args = parser.parse_args()
    
    if args.test_connection:
        success = test_scraper_connection(args.flaresolverr_url)
        print(f"Connection test: {'✓ Success' if success else '✗ Failed'}")
        exit(0 if success else 1)
    
    if not args.riot_id and not args.bulk:
        print("Please provide --riot-id, --bulk, or --test-connection")
        exit(1)
    
    scraper = EnhancedValorantScraper(args.flaresolverr_url)
    
    async def main():
        if args.bulk:
            results = await scraper.bulk_smart_update(args.bulk, max_concurrent=2)
            for result in results:
                print(f"{result['riot_id']}: {result['status']}")
        elif args.api_only:
            data = scraper.get_player_api_data(args.riot_id)
            print(f"API capture complete for {args.riot_id}")
        elif args.web_only:
            html = scraper.get_player_profile_page(args.riot_id)
            if html:
                data = scraper.parse_player_overview(html)
                print(f"Web scraping complete for {args.riot_id}")
            else:
                print("Failed to get profile page")
                exit(1)
        elif args.smart_update:
            data = await scraper.smart_update_player(args.riot_id)
            print(f"Smart update complete for {args.riot_id}")
        else:
            data = scraper.get_complete_player_data(args.riot_id)
            print(f"Complete data capture for {args.riot_id}")
        
        if args.output and 'data' in locals():
            with open(args.output, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"Saved to {args.output}")
        
        # Print summary for API results
        if 'data' in locals() and "api_data" in data and "summary" in data["api_data"]:
            summary = data["api_data"]["summary"]
            print(f"API Success rate: {summary['successful']}/{summary['total_endpoints']}")
    
    asyncio.run(main()) 