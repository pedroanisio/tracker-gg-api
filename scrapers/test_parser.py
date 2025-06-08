#!/usr/bin/env python3
"""
Test script to parse sample HTML file offline
This allows testing the parser logic without making live requests
"""

import logging
from bs4 import BeautifulSoup
import sys
import os
from dataclasses import dataclass
from typing import Optional

# Simple data class to avoid dependency issues
@dataclass
class ValorantPlayerStats:
    username: str
    platform: str = "pc"
    season: str = "current"
    current_rank: str = "Unranked"
    peak_rank: str = "Unknown"
    wins: int = 0
    matches_played: int = 0
    kd_ratio: float = 0.0
    damage_per_round: float = 0.0
    headshot_percentage: float = 0.0
    win_percentage: float = 0.0

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_sample_html(html_content: str, username: str = "apolloZ#sun") -> ValorantPlayerStats:
    """
    Parse the sample HTML content using BeautifulSoup
    This simulates what the actual parser would do with live data
    """
    logger.info(f"Parsing sample HTML for {username}")
    logger.info(f"HTML content length: {len(html_content)} characters")
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    logger.info("HTML parsing completed successfully")
    
    # Extract actual username from page (more reliable than input)
    username_elem = soup.select_one('[data-copytext], .v3-trnign')
    if username_elem:
        actual_username = username_elem.get('data-copytext') or username_elem.get_text().strip()
        logger.info(f"Found actual username: {actual_username}")
    else:
        actual_username = username
        logger.warning("Could not extract username from page, using input username")
    
    # Initialize result object
    stats = ValorantPlayerStats(
        username=actual_username,
        platform="pc",
        season="current",
        current_rank="Unranked",
        peak_rank="Unknown",
        wins=0,
        matches_played=0,
        kd_ratio=0.0,
        damage_per_round=0.0,
        headshot_percentage=0.0,
        win_percentage=0.0
    )
    
    # Extract current rank and RR
    logger.info("Extracting current rank information...")
    current_rank_elem = soup.select_one('div[data-v-d8000329] .label')
    if current_rank_elem:
        stats.current_rank = current_rank_elem.get_text().strip()
        logger.info(f"Found current rank: {stats.current_rank}")
    else:
        logger.warning("Current rank element not found")
    
    # Extract peak rank
    logger.info("Extracting peak rank information...")
    peak_rank_elem = soup.select_one('.highlight__label')
    if peak_rank_elem and 'peak' in peak_rank_elem.get_text().lower():
        peak_value_elem = peak_rank_elem.find_next('.highlight__value')
        if peak_value_elem:
            stats.peak_rank = peak_value_elem.get_text().strip()
            logger.info(f"Found peak rank: {stats.peak_rank}")
    else:
        logger.warning("Peak rank element not found")
    
    # Extract main statistics from "giant stats" area
    logger.info("Extracting main statistics...")
    giant_stats = soup.select('.giant-stats .stat, .highlighted-stats .stat')
    
    if not giant_stats:
        # Fallback to regular stats
        giant_stats = soup.select('.stat')
        logger.info(f"Using fallback stats selector, found {len(giant_stats)} stat elements")
    else:
        logger.info(f"Found {len(giant_stats)} giant stat elements")
    
    for stat_elem in giant_stats:
        stat_name_elem = stat_elem.select_one('.name, .stat__label, [title]')
        stat_value_elem = stat_elem.select_one('.value, .stat__value, .stat__number')
        
        if not stat_name_elem or not stat_value_elem:
            continue
            
        stat_name = (stat_name_elem.get('title') or stat_name_elem.get_text()).strip().lower()
        stat_value = stat_value_elem.get_text().strip()
        
        logger.debug(f"Processing stat: {stat_name} = {stat_value}")
        
        if 'damage/round' in stat_name or 'adr' in stat_name:
            stats.damage_per_round = extract_number_from_text(stat_value)
            logger.info(f"Found Damage/Round: {stats.damage_per_round}")
        elif 'k/d ratio' in stat_name or 'k/d' in stat_name:
            stats.kd_ratio = extract_number_from_text(stat_value)
            logger.info(f"Found K/D ratio: {stats.kd_ratio}")
        elif 'headshot %' in stat_name or 'headshot' in stat_name:
            stats.headshot_percentage = extract_number_from_text(stat_value)
            logger.info(f"Found headshot percentage: {stats.headshot_percentage}")
        elif 'win %' in stat_name or 'win rate' in stat_name:
            stats.win_percentage = extract_number_from_text(stat_value)
            logger.info(f"Found win percentage: {stats.win_percentage}")
        elif 'wins' in stat_name:
            stats.wins = int(extract_number_from_text(stat_value))
            logger.info(f"Found wins: {stats.wins}")
        elif 'matches' in stat_name or 'games' in stat_name:
            stats.matches_played = int(extract_number_from_text(stat_value))
            logger.info(f"Found matches played: {stats.matches_played}")
    
    logger.info(f"Successfully extracted stats for {actual_username}")
    logger.info(f"Summary - Rank: {stats.current_rank}, Peak: {stats.peak_rank}, "
               f"K/D: {stats.kd_ratio}, ADR: {stats.damage_per_round}")
    
    return stats

def extract_number_from_text(text: str) -> float:
    """Extract the first number from a text string"""
    if not text:
        return 0.0
    
    import re
    # Clean the text: remove common suffixes and non-numeric characters
    cleaned_text = re.sub(r'[^\d,.\-+]', ' ', text)
    
    # Find numbers with optional decimal places and commas
    numbers = re.findall(r'[\d,]+\.?\d*', cleaned_text)
    if numbers:
        try:
            return float(numbers[0].replace(',', ''))
        except ValueError:
            return 0.0
    return 0.0

def main():
    """Main test function"""
    try:
        # Read the sample HTML file
        with open('sample.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        logger.info("Sample HTML file loaded successfully")
        
        # Parse the sample HTML
        stats = parse_sample_html(html_content)
        
        # Print results
        print("\n" + "="*50)
        print("SAMPLE HTML PARSER RESULTS")
        print("="*50)
        print(f"Username: {stats.username}")
        print(f"Platform: {stats.platform}")
        print(f"Current Rank: {stats.current_rank}")
        print(f"Peak Rank: {stats.peak_rank}")
        print(f"Wins: {stats.wins}")
        print(f"Matches Played: {stats.matches_played}")
        print(f"K/D Ratio: {stats.kd_ratio}")
        print(f"Damage/Round: {stats.damage_per_round}")
        print(f"Headshot %: {stats.headshot_percentage}")
        print(f"Win %: {stats.win_percentage}")
        print("="*50)
        
    except FileNotFoundError:
        logger.error("sample.html file not found. Make sure it exists in the current directory.")
    except Exception as e:
        logger.error(f"Error during parsing: {e}")

if __name__ == "__main__":
    main() 