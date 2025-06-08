"""
Enhanced Valorant scraper with anti-detection techniques and smart update strategies.
Optimized for avoiding tracker.gg rate limiting and detection.
"""

import asyncio
import random
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urljoin
import requests
from sqlmodel import Session, select

from .flaresolverr_client import FlareSolverrClient
from .valorant_scraper import ValorantScraper
from ..shared.database import get_session, Player, DataIngestionLog
from ..shared.models import TrackerAPIConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UpdateCheckpoint:
    """Checkpoint for tracking update progress."""
    player_id: str
    last_update: datetime
    endpoints_fetched: Set[str]
    priority_score: float
    retry_count: int = 0

class EnhancedAntiDetectionScraper:
    """Enhanced scraper with anti-detection and smart update strategies."""
    
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
        
        # Anti-detection settings
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
        ]
        
        # Request timing settings
        self.min_delay = 1.0  # Minimum delay between requests
        self.max_delay = 3.0  # Maximum delay between requests
        self.backoff_multiplier = 2.0  # Exponential backoff multiplier
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
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.user_agents)
    
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
        time_since_update = datetime.utcnow() - player.last_updated
        
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
                attempt_headers["user-agent"] = self.get_random_user_agent()
                
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
                            "timestamp": datetime.utcnow().isoformat()
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
        username, tag = riot_id.split('#') if '#' in riot_id else (riot_id, '')
        encoded_riot_id = f"{username}%23{tag}"
        base_url = "https://api.tracker.gg"
        
        # Create or get checkpoint
        checkpoint = self.create_checkpoint(riot_id, datetime.utcnow())
        
        # Enhanced headers with anti-detection
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,en-GB;q=0.8",
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
            "user-agent": self.get_random_user_agent()
        }
        
        # Define endpoints with priorities
        all_endpoints = {
            "v1_competitive_aggregated": f"{base_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=competitive&source=web",
            "v1_premier_aggregated": f"{base_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=premier&source=web",
            "v1_unrated_aggregated": f"{base_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=unrated&source=web",
            "v2_competitive_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=competitive&source=web",
            "v2_premier_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=premier&source=web",
            "v2_unrated_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=unrated&source=web",
            "v2_deathmatch_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=deathmatch&source=web",
            "v2_loadout_segments": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/loadout?source=web"
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
                "user_agent": self.get_random_user_agent()
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
        checkpoint.last_update = datetime.utcnow()
        if successful_fetches == 0:
            checkpoint.retry_count += 1
        else:
            checkpoint.retry_count = 0
        
        return {
            "riot_id": riot_id,
            "update_timestamp": datetime.utcnow().isoformat(),
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
                processed_results.append({
                    "riot_id": players_to_update[i],
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results


# API endpoint for enhanced updating
async def enhanced_update_player_data(riot_id: str) -> Dict[str, Any]:
    """
    Enhanced update function for use in API endpoints.
    
    Args:
        riot_id: Player's Riot ID
        
    Returns:
        Update result
    """
    scraper = EnhancedAntiDetectionScraper()
    
    try:
        result = await scraper.smart_update_player(riot_id, checkpoint_only_recent=True)
        
        # Save successful data to files for processing
        if result["summary"]["successful"] > 0:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = Path(f"data/enhanced_update_{riot_id.replace('#', '_')}_{timestamp}.json")
            output_file.parent.mkdir(exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Enhanced update data saved to {output_file}")
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced update failed for {riot_id}: {e}")
        return {
            "riot_id": riot_id,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 