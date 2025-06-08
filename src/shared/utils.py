"""
Shared utilities across the application.
"""

import logging
import os
import random
from datetime import datetime
from typing import Optional, Dict, Any, List


# API Constants
TRACKER_API_BASE_URL = "https://api.tracker.gg"
TRACKER_WEB_BASE_URL = "https://tracker.gg"

# Common API endpoints patterns
API_ENDPOINTS = {
    "v1_aggregated": "/api/v1/valorant/standard/profile/riot/{riot_id}/aggregated",
    "v2_playlist": "/api/v2/valorant/standard/profile/riot/{riot_id}/segments/playlist",
    "v2_loadout": "/api/v2/valorant/standard/profile/riot/{riot_id}/segments/loadout",
    "profile_page": "/valorant/profile/riot/{riot_id}/overview"
}


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up logger with consistent configuration across the application.
    
    Args:
        name: Logger name (typically __name__)
        level: Log level override (defaults to INFO or LOG_LEVEL env var)
    
    Returns:
        Configured logger instance
    """
    # Configure logging only once
    if not logging.getLogger().handlers:
        log_level = level or os.getenv("LOG_LEVEL", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    return logging.getLogger(name)


def parse_riot_id(riot_id: str) -> tuple[str, str]:
    """
    Parse Riot ID into username and tag components.
    
    Args:
        riot_id: Riot ID in format "username#tag"
    
    Returns:
        Tuple of (username, tag)
    """
    if '#' in riot_id:
        username, tag = riot_id.split('#', 1)  # Split only on first #
        return username, tag
    return riot_id, ''


def encode_riot_id(riot_id: str) -> str:
    """
    URL encode Riot ID for API requests.
    
    Args:
        riot_id: Riot ID in format "username#tag"
    
    Returns:
        URL encoded riot ID with %23 replacing #
    """
    username, tag = parse_riot_id(riot_id)
    return f"{username}%23{tag}" if tag else username


def get_current_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.
    
    Returns:
        Current timestamp as ISO string
    """
    return datetime.utcnow().isoformat()


def get_current_datetime() -> datetime:
    """
    Get current UTC datetime object.
    
    Returns:
        Current datetime in UTC
    """
    return datetime.utcnow()


def build_api_url(endpoint_key: str, riot_id: str, **params) -> str:
    """
    Build API URL from endpoint pattern and parameters.
    
    Args:
        endpoint_key: Key from API_ENDPOINTS
        riot_id: Riot ID (will be URL encoded)
        **params: Additional query parameters
    
    Returns:
        Complete API URL
    """
    if endpoint_key not in API_ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint_key}")
    
    encoded_riot_id = encode_riot_id(riot_id)
    endpoint_path = API_ENDPOINTS[endpoint_key].format(riot_id=encoded_riot_id)
    base_url = TRACKER_API_BASE_URL + endpoint_path
    
    # Add query parameters
    if params:
        query_params = []
        for key, value in params.items():
            if value is not None:
                query_params.append(f"{key}={value}")
        if query_params:
            base_url += "?" + "&".join(query_params)
    
    return base_url


def create_success_response(riot_id: str, data: Dict[str, Any], **extra) -> Dict[str, Any]:
    """
    Create standardized success response.
    
    Args:
        riot_id: Player's Riot ID
        data: Response data
        **extra: Additional response fields
    
    Returns:
        Standardized success response
    """
    response = {
        "status": "success",
        "riot_id": riot_id,
        "timestamp": get_current_timestamp(),
        **data,
        **extra
    }
    return response


def create_error_response(riot_id: str, error: str, **extra) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        riot_id: Player's Riot ID
        error: Error message
        **extra: Additional response fields
    
    Returns:
        Standardized error response
    """
    response = {
        "status": "error",
        "riot_id": riot_id,
        "error": error,
        "timestamp": get_current_timestamp(),
        **extra
    }
    return response


def create_player_info_dict(player, **extra) -> Dict[str, Any]:
    """
    Create standardized player info dictionary.
    
    Args:
        player: Player database object
        **extra: Additional player fields
    
    Returns:
        Player info dictionary
    """
    return {
        "riot_id": player.riot_id,
        "username": player.username,
        "tag": player.tag,
        **extra
    }


# Common User Agents for anti-detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
]


def get_random_user_agent() -> str:
    """
    Get a random realistic user agent for anti-detection.
    
    Returns:
        Random user agent string
    """
    return random.choice(USER_AGENTS)


def get_browser_headers(riot_id: str, user_agent: Optional[str] = None) -> Dict[str, str]:
    """
    Get standard browser headers for tracker.gg requests.
    
    Args:
        riot_id: Riot ID for referer header
        user_agent: Custom user agent (random if None)
    
    Returns:
        Dictionary of HTTP headers
    """
    encoded_riot_id = encode_riot_id(riot_id)
    referer = f"{TRACKER_WEB_BASE_URL}/valorant/profile/riot/{encoded_riot_id}/overview"
    
    return {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "dnt": "1",
        "pragma": "no-cache",
        "referer": referer,
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": user_agent or get_random_user_agent()
    }


def get_api_headers(riot_id: str, user_agent: Optional[str] = None) -> Dict[str, str]:
    """
    Get standard API headers for tracker.gg API requests.
    
    Args:
        riot_id: Riot ID for referer header
        user_agent: Custom user agent (random if None)
    
    Returns:
        Dictionary of HTTP headers for API calls
    """
    encoded_riot_id = encode_riot_id(riot_id)
    referer = f"{TRACKER_WEB_BASE_URL}/valorant/profile/riot/{encoded_riot_id}/overview"
    
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "dnt": "1",
        "origin": TRACKER_WEB_BASE_URL,
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": referer,
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": user_agent or get_random_user_agent()
    } 