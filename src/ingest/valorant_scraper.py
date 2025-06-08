"""
Valorant scraper for tracker.gg using BeautifulSoup and FlareSolverr.
Handles both web scraping and API data capture.
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
import json
import time
import logging
from urllib.parse import urljoin
from .flaresolverr_client import FlareSolverrClient
from ..shared.models import TrackerAPIConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValorantScraper:
    """Scraper for Valorant player data from tracker.gg."""
    
    def __init__(self, flaresolverr_url: str = "http://localhost:8191"):
        """
        Initialize the scraper.
        
        Args:
            flaresolverr_url: URL of the FlareSolverr service
        """
        self.flaresolverr_url = flaresolverr_url
        self.base_url = "https://tracker.gg"
        self.api_base_url = "https://api.tracker.gg"
        
    def get_player_profile_page(self, riot_id: str) -> Optional[str]:
        """
        Get the HTML content of a player's profile page.
        
        Args:
            riot_id: Player's Riot ID (username#tag)
            
        Returns:
            HTML content or None if failed
        """
        
        username, tag = riot_id.split('#') if '#' in riot_id else (riot_id, '')
        encoded_riot_id = f"{username}%23{tag}"
        profile_url = f"{self.base_url}/valorant/profile/riot/{encoded_riot_id}/overview"
        
        try:
            with FlareSolverrClient(self.flaresolverr_url) as client:
                result = client.get_request(profile_url)
                
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
            return {"error": str(e)}
    
    def get_complete_player_data(self, riot_id: str) -> Dict[str, Any]:
        """
        Get complete player data including both web scraping and API data.
        
        Args:
            riot_id: Player's Riot ID (username#tag)
            
        Returns:
            Combined player data
        """
        
        result = {
            "riot_id": riot_id,
            "scraping_timestamp": time.time(),
            "web_data": {},
            "api_data": {},
            "status": "success"
        }
        
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
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Error getting complete player data: {e}")
        
        return result
    
    def test_connection(self) -> bool:
        """
        Test if the scraper can connect to tracker.gg.
        
        Returns:
            True if connection successful, False otherwise
        """
        
        try:
            with FlareSolverrClient(self.flaresolverr_url) as client:
                result = client.get_request(self.base_url)
                solution = result.get("solution", {})
                return solution.get("status") == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


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
    
    scraper = ValorantScraper(flaresolverr_url)
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
    
    scraper = ValorantScraper(flaresolverr_url)
    return scraper.test_connection()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Valorant tracker.gg scraper")
    parser.add_argument("--riot-id", help="Riot ID to scrape (e.g., 'player#1234')")
    parser.add_argument("--flaresolverr-url", default="http://localhost:8191", help="FlareSolverr URL")
    parser.add_argument("--output", help="Output file for scraped data")
    parser.add_argument("--test-connection", action="store_true", help="Test connection only")
    parser.add_argument("--api-only", action="store_true", help="Only capture API data")
    parser.add_argument("--web-only", action="store_true", help="Only scrape web data")
    
    args = parser.parse_args()
    
    if args.test_connection:
        success = test_scraper_connection(args.flaresolverr_url)
        print(f"Connection test: {'✓ Success' if success else '✗ Failed'}")
        exit(0 if success else 1)
    
    if not args.riot_id:
        print("Please provide --riot-id or --test-connection")
        exit(1)
    
    scraper = ValorantScraper(args.flaresolverr_url)
    
    if args.api_only:
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
    else:
        data = scraper.get_complete_player_data(args.riot_id)
        print(f"Complete data capture for {args.riot_id}")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved to {args.output}")
    
    # Print summary
    if "api_data" in data and "summary" in data["api_data"]:
        summary = data["api_data"]["summary"]
        print(f"API Success rate: {summary['successful']}/{summary['total_endpoints']}") 