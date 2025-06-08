import re
import logging
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import quote
from models.valorant_model import ValorantPlayerStats, Weapon, MapStats, Role
from flaresolverr_client import fetch_page_with_flaresolverr

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://tracker.gg/valorant/profile/riot"


def sanitize_number(value: str) -> float:
    """
    Remove commas from a numeric string and convert it to a float.
    Return 0.0 if the value cannot be converted.
    """
    try:
        return float(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def extract_number_from_text(text: str) -> float:
    """
    Extract the first number from a text string.
    Handles various formats: "1,234.5", "42.0%", "97RR", etc.
    """
    if not text:
        return 0.0
    
    # Clean the text: remove common suffixes and non-numeric characters
    cleaned_text = re.sub(r'[^\d,.\-+]', ' ', text)
    
    # Find numbers with optional decimal places and commas
    numbers = re.findall(r'[\d,]+\.?\d*', cleaned_text)
    if numbers:
        try:
            # Remove commas and convert to float
            return float(numbers[0].replace(',', ''))
        except ValueError:
            return 0.0
    return 0.0


async def fetch_valorant_player_stats(username: str, season: Optional[str] = None) -> Optional[ValorantPlayerStats]:
    """
    Fetch Valorant player statistics from tracker.gg with enhanced parsing and detailed logging.
    
    Args:
        username: The player's username (e.g., "player#1234")
        season: Optional season filter
    
    Returns:
        ValorantPlayerStats object or None if player not found
    """
    logger.info(f"Starting to fetch Valorant stats for player: {username}")
    
    # URL encode the username
    encoded_username = quote(username)
    url = f"{BASE_URL}/{encoded_username}"
    
    if season:
        url += f"?season={season}"
    
    logger.info(f"Constructed URL: {url}")
    
    try:
        logger.info("Sending request to FlareSolverr...")
        response = await fetch_page_with_flaresolverr(url)
        
        if not response:
            logger.error("Failed to get response from FlareSolverr")
            return None
        
        logger.info(f"Received response with content length: {len(response)} characters")
        
        # Parse HTML
        logger.info("Parsing HTML content with BeautifulSoup...")
        soup = BeautifulSoup(response, 'html.parser')
        logger.info("HTML parsing completed successfully")
        
        # Extract actual username from page (more reliable than input)
        username_elem = soup.select_one('[data-copytext], .v3-trnign')
        if username_elem:
            actual_username = username_elem.get('data-copytext') or username_elem.get_text().strip()
            logger.info(f"Found actual username: {actual_username}")
        else:
            actual_username = username
            logger.warning("Could not extract username from page, using input")
        
        # Initialize result object
        stats = ValorantPlayerStats(
            username=actual_username,
            platform="pc",  # Adding required platform field
            season=season or "current",
            current_rank="Unranked",
            peak_rank="Unknown",
            wins=0,
            matches_played=0,
            kd_ratio=0.0,
            damage_per_round=0.0,
            acs=0.0,
            headshot_percentage=0.0,
            win_percentage=0.0,
            top_weapons=[],
            top_maps=[],
            roles=[]
        )
        
        # Extract current rank and RR
        logger.info("Extracting current rank information...")
        current_rank_elem = soup.select_one('div[data-v-d8000329] .label')
        if current_rank_elem:
            stats.current_rank = current_rank_elem.get_text().strip()
            logger.info(f"Found current rank: {stats.current_rank}")
        else:
            logger.warning("Current rank element not found")
        
        # Extract current RR (note: not stored as model doesn't have this field)
        rr_elem = soup.select_one('span.mmr')
        if rr_elem:
            rr_text = rr_elem.get_text().strip()
            current_rr = extract_number_from_text(rr_text)
            logger.info(f"Found current RR: {current_rr}")
        else:
            logger.warning("Current RR element not found")
        
        # Extract peak rank
        logger.info("Extracting peak rank information...")
        peak_rank_section = soup.find('h3', text='Peak Rating')
        if peak_rank_section:
            peak_container = peak_rank_section.find_next('div', class_='rating-entry')
            if peak_container:
                peak_rank_elem = peak_container.select_one('.value')
                if peak_rank_elem:
                    stats.peak_rank = peak_rank_elem.get_text().strip()
                    logger.info(f"Found peak rank: {stats.peak_rank}")
        else:
            logger.warning("Peak rank section not found")
        
        # Extract level (note: not stored as model doesn't have this field)
        logger.info("Extracting player level...")
        # Look for level in the highlighted content area
        level_elem = soup.select_one('.stat__label:contains("Level"), [title="Level"]')
        if level_elem:
            level_value_elem = level_elem.find_next('.stat__value')
            if level_value_elem:
                level = int(extract_number_from_text(level_value_elem.get_text()))
                logger.info(f"Found level: {level}")
        else:
            logger.warning("Level element not found")
        
        # Extract main statistics from giant stats area
        logger.info("Extracting main statistics...")
        # Try giant stats first (main overview stats)
        giant_stat_elements = soup.select('.giant-stats .stat, .stat.giant')
        if not giant_stat_elements:
            # Fallback to regular stats
            giant_stat_elements = soup.select('.stat')
        
        logger.info(f"Found {len(giant_stat_elements)} stat elements")
        
        for stat_elem in giant_stat_elements:
            stat_name_elem = stat_elem.select_one('.name, .stat__label, [title]')
            stat_value_elem = stat_elem.select_one('.value, .stat__value')
            
            if not stat_name_elem or not stat_value_elem:
                continue
            
            # Get stat name from text or title attribute
            stat_name = (stat_name_elem.get('title') or stat_name_elem.get_text()).strip().lower()
            stat_value = stat_value_elem.get_text().strip()
            
            logger.debug(f"Processing stat: {stat_name} = {stat_value}")
            
            if 'damage/round' in stat_name or 'adr' in stat_name:
                stats.damage_per_round = extract_number_from_text(stat_value)
                logger.info(f"Found damage per round: {stats.damage_per_round}")
            elif 'k/d ratio' in stat_name:
                stats.kd_ratio = extract_number_from_text(stat_value)
                logger.info(f"Found K/D ratio: {stats.kd_ratio}")
            elif 'headshot %' in stat_name:
                stats.headshot_percentage = extract_number_from_text(stat_value)
                logger.info(f"Found headshot percentage: {stats.headshot_percentage}")
            elif 'win %' in stat_name:
                stats.win_percentage = extract_number_from_text(stat_value)
                logger.info(f"Found win percentage: {stats.win_percentage}")
            elif 'acs' in stat_name:
                stats.acs = extract_number_from_text(stat_value)
                logger.info(f"Found ACS: {stats.acs}")
            elif stat_name == 'wins':
                stats.wins = int(extract_number_from_text(stat_value))
                logger.info(f"Found wins: {stats.wins}")
        
        # Extract weapons data
        logger.info("Extracting weapons data...")
        weapon_elements = soup.select('.weapon')
        logger.info(f"Found {len(weapon_elements)} weapon elements")
        
        for weapon_elem in weapon_elements:
            weapon_name_elem = weapon_elem.select_one('.weapon__name')
            weapon_type_elem = weapon_elem.select_one('.weapon__type')
            weapon_kills_elem = weapon_elem.select_one('.weapon__main-stat .value')
            weapon_silhouette_elem = weapon_elem.select_one('.weapon__silhouette')
            weapon_accuracy_elems = weapon_elem.select('.weapon__accuracy-hits .stat')
            
            if weapon_name_elem and weapon_kills_elem:
                weapon_name = weapon_name_elem.get_text().strip()
                weapon_type = weapon_type_elem.get_text().strip() if weapon_type_elem else "Unknown"
                weapon_kills = int(extract_number_from_text(weapon_kills_elem.get_text()))
                weapon_silhouette_url = weapon_silhouette_elem.get('src', '') if weapon_silhouette_elem else ""
                weapon_accuracy = [elem.get_text().strip() for elem in weapon_accuracy_elems] if weapon_accuracy_elems else []
                
                weapon = Weapon(
                    weapon_name=weapon_name,
                    weapon_type=weapon_type,
                    weapon_silhouette_url=weapon_silhouette_url,
                    weapon_accuracy=weapon_accuracy,
                    weapon_kills=weapon_kills
                )
                stats.top_weapons.append(weapon)
                logger.debug(f"Added weapon: {weapon_name} ({weapon_type}) with {weapon_kills} kills")
        
        logger.info(f"Extracted {len(stats.top_weapons)} weapons")
        
        # Extract maps data
        logger.info("Extracting maps data...")
        map_elements = soup.select('.top-maps__maps-map')
        logger.info(f"Found {len(map_elements)} map elements")
        
        for map_elem in map_elements:
            map_name_elem = map_elem.select_one('.name')
            map_win_rate_elem = map_elem.select_one('.value')
            map_matches_elem = map_elem.select_one('.label')
            
            if map_name_elem and map_win_rate_elem:
                map_name = map_name_elem.get_text().strip()
                map_win_percentage = map_win_rate_elem.get_text().strip()
                map_matches = map_matches_elem.get_text().strip() if map_matches_elem else "Unknown"
                
                # Try to extract background image from style attribute
                map_image_url = ""
                style_attr = map_elem.get('style', '')
                if 'background-image-url' in style_attr:
                    url_match = re.search(r"url\('([^']+)'\)", style_attr)
                    if url_match:
                        map_image_url = url_match.group(1)
                
                map_stat = MapStats(
                    map_name=map_name,
                    map_win_percentage=map_win_percentage,
                    map_matches=map_matches,
                    map_image_url=map_image_url
                )
                stats.top_maps.append(map_stat)
                logger.debug(f"Added map: {map_name} with win rate {map_win_percentage}")
        
        logger.info(f"Extracted {len(stats.top_maps)} maps")
        
        # Extract roles data
        logger.info("Extracting roles data...")
        role_elements = soup.select('.role')
        logger.info(f"Found {len(role_elements)} role elements")
        
        for role_elem in role_elements:
            role_name_elem = role_elem.select_one('.role__name')
            role_image_elem = role_elem.select_one('.icon, img')
            
            if role_name_elem:
                role_name = role_name_elem.get_text().strip()
                role_image_url = role_image_elem.get('src', '') if role_image_elem else ""
                
                # Look for stats in role stats - extract what we can
                role_stats = role_elem.select('.role__stat .role__value')
                
                role_win_rate = "0%"
                role_kda = 0.0
                role_wins = 0
                role_losses = 0
                role_kills = 0
                role_deaths = 0
                role_assists = 0
                
                for stat in role_stats:
                    stat_text = stat.get_text().strip()
                    if 'WR' in stat_text or '%' in stat_text:
                        role_win_rate = stat_text
                    elif 'KDA' in stat_text:
                        role_kda = extract_number_from_text(stat_text)
                
                # Extract win/loss from role sub text if available
                role_sub_elem = role_elem.select_one('.role__sub')
                if role_sub_elem:
                    sub_text = role_sub_elem.get_text().strip()
                    wins_match = re.search(r'(\d+)W', sub_text)
                    losses_match = re.search(r'(\d+)L', sub_text)
                    kda_match = re.search(r'(\d+)/(\d+)/(\d+)', sub_text)
                    
                    if wins_match:
                        role_wins = int(wins_match.group(1))
                    if losses_match:
                        role_losses = int(losses_match.group(1))
                    if kda_match:
                        role_kills = int(kda_match.group(1))
                        role_deaths = int(kda_match.group(2))
                        role_assists = int(kda_match.group(3))
                
                role = Role(
                    role_name=role_name,
                    role_win_rate=role_win_rate,
                    role_kda=role_kda,
                    role_wins=role_wins,
                    role_losses=role_losses,
                    role_kills=role_kills,
                    role_deaths=role_deaths,
                    role_assists=role_assists,
                    role_image_url=role_image_url
                )
                stats.roles.append(role)
                logger.debug(f"Added role: {role_name} with win rate {role_win_rate}")
        
        logger.info(f"Extracted {len(stats.roles)} roles")
        
        # Calculate matches played from wins and win percentage
        if stats.win_percentage and stats.win_percentage > 0 and stats.wins:
            stats.matches_played = int(stats.wins / (stats.win_percentage / 100))
            logger.info(f"Calculated matches played: {stats.matches_played}")
        
        logger.info(f"Successfully extracted stats for {username}")
        logger.info(f"Summary - Rank: {stats.current_rank}, "
                   f"Damage/Round: {stats.damage_per_round}, K/D: {stats.kd_ratio}, "
                   f"Weapons: {len(stats.top_weapons)}, Maps: {len(stats.top_maps)}, Roles: {len(stats.roles)}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching stats for {username}: {str(e)}", exc_info=True)
        return None
