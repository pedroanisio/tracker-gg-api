"""
FlareSolverr client for bypassing Cloudflare protection on tracker.gg.
Used for data ingestion and API capture.
"""

import requests
import json
import time
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_json_from_html(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from HTML wrapper that FlareSolverr returns.
    
    Args:
        html_content: HTML content from FlareSolverr
        
    Returns:
        Parsed JSON data or None if extraction fails
    """
    try:
        # Look for JSON content between <pre> tags
        pre_pattern = r'<pre[^>]*>(.*?)</pre>'
        match = re.search(pre_pattern, html_content, re.DOTALL)
        
        if match:
            json_content = match.group(1).strip()
            try:
                return json.loads(json_content)
            except json.JSONDecodeError:
                pass
        
        # Fallback: try to find JSON pattern directly
        json_pattern = r'\{.*\}'
        json_match = re.search(json_pattern, html_content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Final fallback: check if the content is already JSON
        try:
            return json.loads(html_content)
        except json.JSONDecodeError:
            return None
            
    except Exception as e:
        logger.error(f"Error extracting JSON from HTML: {e}")
        return None


class FlareSolverrClient:
    """Client for interacting with FlareSolverr to bypass Cloudflare protection."""
    
    def __init__(self, flaresolverr_url: str = "http://localhost:8191", timeout: int = 60):
        """
        Initialize FlareSolverr client.
        
        Args:
            flaresolverr_url: URL of the FlareSolverr service
            timeout: Request timeout in seconds
        """
        self.flaresolverr_url = flaresolverr_url.rstrip('/')
        self.timeout = timeout
        self.session_id = None
        
    def create_session(self, 
                      user_agent: Optional[str] = None,
                      proxy: Optional[str] = None) -> Dict[str, Any]:
        """Create a new browser session."""
        
        payload = {
            "cmd": "sessions.create",
            "userAgent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "maxTimeout": self.timeout * 1000  # Convert to milliseconds
        }
        
        if proxy:
            payload["proxy"] = proxy
            
        response = requests.post(
            f"{self.flaresolverr_url}/v1",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") == "ok":
            self.session_id = result.get("session")
            logger.info(f"Created FlareSolverr session: {self.session_id}")
            return result
        else:
            raise Exception(f"Failed to create session: {result}")
    
    def destroy_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Destroy a browser session."""
        
        session_to_destroy = session_id or self.session_id
        if not session_to_destroy:
            raise ValueError("No session ID provided or available")
            
        payload = {
            "cmd": "sessions.destroy",
            "session": session_to_destroy
        }
        
        response = requests.post(
            f"{self.flaresolverr_url}/v1",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") == "ok":
            if session_to_destroy == self.session_id:
                self.session_id = None
            logger.info(f"Destroyed FlareSolverr session: {session_to_destroy}")
            return result
        else:
            logger.warning(f"Failed to destroy session: {result}")
            return result
    
    def get_request(self, 
                   url: str, 
                   headers: Optional[Dict[str, str]] = None,
                   cookies: Optional[List[Dict[str, str]]] = None,
                   return_only_cookies: bool = False,
                   max_timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Make a GET request through FlareSolverr.
        
        Args:
            url: URL to request
            headers: Optional headers (ignored in FlareSolverr v2+)
            cookies: Optional cookies to include
            return_only_cookies: If True, only return cookies
            max_timeout: Optional timeout override
            
        Returns:
            Response data from FlareSolverr
        """
        
        if not self.session_id:
            self.create_session()
            
        payload = {
            "cmd": "request.get",
            "url": url,
            "session": self.session_id,
            "maxTimeout": (max_timeout or self.timeout) * 1000
        }
        
        # Note: FlareSolverr v2+ removed support for custom headers
        # Only include cookies and returnOnlyCookies if specified
        if cookies:
            payload["cookies"] = cookies
        if return_only_cookies:
            payload["returnOnlyCookies"] = True
            
        response = requests.post(
            f"{self.flaresolverr_url}/v1",
            json=payload,
            timeout=(max_timeout or self.timeout) + 10  # Add buffer for FlareSolverr processing
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") != "ok":
            raise Exception(f"FlareSolverr request failed: {result}")
            
        return result
    
    def post_request(self, 
                    url: str,
                    post_data: Optional[str] = None,
                    headers: Optional[Dict[str, str]] = None,
                    cookies: Optional[List[Dict[str, str]]] = None,
                    return_only_cookies: bool = False,
                    max_timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Make a POST request through FlareSolverr.
        
        Args:
            url: URL to request
            post_data: POST data as string
            headers: Optional headers to include
            cookies: Optional cookies to include
            return_only_cookies: If True, only return cookies
            max_timeout: Optional timeout override
            
        Returns:
            Response data from FlareSolverr
        """
        
        if not self.session_id:
            self.create_session()
            
        payload = {
            "cmd": "request.post",
            "url": url,
            "session": self.session_id,
            "maxTimeout": (max_timeout or self.timeout) * 1000
        }
        
        if post_data:
            payload["postData"] = post_data
        if headers:
            payload["headers"] = headers
        if cookies:
            payload["cookies"] = cookies
        if return_only_cookies:
            payload["returnOnlyCookies"] = True
            
        response = requests.post(
            f"{self.flaresolverr_url}/v1",
            json=payload,
            timeout=(max_timeout or self.timeout) + 10
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") != "ok":
            raise Exception(f"FlareSolverr POST request failed: {result}")
            
        return result
    
    def capture_tracker_api(self, 
                           riot_id: str,
                           base_url: str = "https://api.tracker.gg") -> Dict[str, Any]:
        """
        Capture tracker.gg API data for a player.
        
        Args:
            riot_id: Player's Riot ID (username#tag)
            base_url: Base API URL
            
        Returns:
            Dictionary containing all captured API responses
        """
        
        username, tag = riot_id.split('#') if '#' in riot_id else (riot_id, '')
        encoded_riot_id = f"{username}%23{tag}"
        
        # Common headers for tracker.gg API
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "dnt": "1",
            "origin": "https://tracker.gg",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": f"https://tracker.gg/valorant/profile/riot/{encoded_riot_id}/overview",
            "sec-ch-ua": '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # API endpoints to test
        endpoints = {
            # V1 aggregated endpoints
            "v1_competitive_aggregated": f"{base_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=competitive&source=web",
            "v1_premier_aggregated": f"{base_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=premier&source=web",
            "v1_unrated_aggregated": f"{base_url}/api/v1/valorant/standard/profile/riot/{encoded_riot_id}/aggregated?playlist=unrated&source=web",
            
            # V2 playlist endpoints
            "v2_competitive_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=competitive&source=web",
            "v2_premier_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=premier&source=web",
            "v2_unrated_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=unrated&source=web",
            "v2_deathmatch_playlist": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/playlist?playlist=deathmatch&source=web",
            
            # V2 loadout endpoints
            "v2_loadout_segments": f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_riot_id}/segments/loadout?source=web"
        }
        
        results = {}
        
        # Create session first
        self.create_session()
        
        try:
            for endpoint_name, url in endpoints.items():
                try:
                    logger.info(f"Capturing {endpoint_name}: {url}")
                    
                    result = self.get_request(url, headers=headers)
                    
                    # Parse the response
                    solution = result.get("solution", {})
                    response_text = solution.get("response", "")
                    status_code = solution.get("status", 0)
                    
                    if status_code == 200 and response_text:
                        try:
                            api_data = json.loads(response_text)
                            results[endpoint_name] = {
                                "url": url,
                                "status": "success",
                                "status_code": status_code,
                                "data": api_data
                            }
                            logger.info(f"✓ {endpoint_name}: Success")
                        except json.JSONDecodeError as e:
                            results[endpoint_name] = {
                                "url": url,
                                "status": "json_error",
                                "status_code": status_code,
                                "error": str(e),
                                "raw_response": response_text[:500]  # First 500 chars
                            }
                            logger.error(f"✗ {endpoint_name}: JSON decode error - {e}")
                    else:
                        results[endpoint_name] = {
                            "url": url,
                            "status": "http_error",
                            "status_code": status_code,
                            "raw_response": response_text[:500] if response_text else "No response"
                        }
                        logger.error(f"✗ {endpoint_name}: HTTP {status_code}")
                        
                    # Small delay between requests
                    time.sleep(0.5)
                    
                except Exception as e:
                    results[endpoint_name] = {
                        "url": url,
                        "status": "error",
                        "error": str(e)
                    }
                    logger.error(f"✗ {endpoint_name}: Exception - {e}")
                    
        finally:
            # Clean up session
            self.destroy_session()
            
        return {
            "riot_id": riot_id,
            "capture_timestamp": time.time(),
            "endpoints": results,
            "summary": {
                "total_endpoints": len(endpoints),
                "successful": len([r for r in results.values() if r.get("status") == "success"]),
                "failed": len([r for r in results.values() if r.get("status") != "success"])
            }
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up session."""
        if self.session_id:
            try:
                self.destroy_session()
            except Exception as e:
                logger.warning(f"Failed to clean up session on exit: {e}")


# Utility functions for common operations
def capture_player_data(riot_id: str, 
                       flaresolverr_url: str = "http://localhost:8191",
                       output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture all available data for a player.
    
    Args:
        riot_id: Player's Riot ID
        flaresolverr_url: FlareSolverr service URL
        output_file: Optional file to save results
        
    Returns:
        Captured data dictionary
    """
    
    with FlareSolverrClient(flaresolverr_url) as client:
        data = client.capture_tracker_api(riot_id)
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved data to {output_file}")
            
        return data


def test_flaresolverr_connection(flaresolverr_url: str = "http://localhost:8191") -> bool:
    """
    Test if FlareSolverr is running and accessible.
    
    Args:
        flaresolverr_url: FlareSolverr service URL
        
    Returns:
        True if accessible, False otherwise
    """
    
    try:
        client = FlareSolverrClient(flaresolverr_url)
        result = client.create_session()
        client.destroy_session()
        logger.info("FlareSolverr connection test successful")
        return True
    except Exception as e:
        logger.error(f"FlareSolverr connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Test FlareSolverr client")
    parser.add_argument("--riot-id", help="Riot ID to test with (e.g., 'player#1234')")
    parser.add_argument("--url", default="http://localhost:8191", help="FlareSolverr URL")
    parser.add_argument("--output", help="Output file for captured data")
    parser.add_argument("--test-connection", action="store_true", help="Test connection only")
    
    args = parser.parse_args()
    
    if args.test_connection:
        success = test_flaresolverr_connection(args.url)
        exit(0 if success else 1)
    
    if args.riot_id:
        data = capture_player_data(args.riot_id, args.url, args.output)
        print(f"Captured data for {args.riot_id}")
        print(f"Success rate: {data['summary']['successful']}/{data['summary']['total_endpoints']}")
    else:
        print("Please provide --riot-id or --test-connection") 