#!/usr/bin/env python3
"""
HTML Structure Analyzer
Analyzes the sample HTML to find all potential CSS selectors for different data points
"""

import logging
from bs4 import BeautifulSoup
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_html_structure(html_content: str):
    """Analyze HTML structure to find potential selectors"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    print("\n" + "="*60)
    print("HTML STRUCTURE ANALYSIS")
    print("="*60)
    
    # 1. Find all elements with stat-related classes
    print("\n📊 STAT ELEMENTS:")
    stat_elements = soup.find_all(['div', 'span'], class_=re.compile(r'stat|value|number|label', re.I))
    for i, elem in enumerate(stat_elements[:10]):  # Limit output
        text = elem.get_text().strip()[:50]
        classes = ' '.join(elem.get('class', []))
        print(f"  {i+1}. Class: {classes}")
        print(f"     Text: {text}")
        print(f"     Tag: {elem.name}")
        print()
    
    # 2. Find elements containing rank information
    print("\n🏆 RANK ELEMENTS:")
    rank_keywords = ['rank', 'tier', 'immortal', 'radiant', 'diamond', 'peak']
    for keyword in rank_keywords:
        elements = soup.find_all(text=re.compile(keyword, re.I))
        for elem in elements[:3]:  # Limit output
            parent = elem.parent
            if parent:
                print(f"  Keyword: {keyword}")
                print(f"  Text: {elem.strip()}")
                print(f"  Parent: {parent.name} - {parent.get('class', [])}")
                print()
    
    # 3. Find highlighted/featured elements
    print("\n✨ HIGHLIGHTED ELEMENTS:")
    highlight_selectors = [
        '.highlight', '.featured', '.main-stat', '.giant-stat', 
        '.primary', '.hero', '.header-stat', '.overview'
    ]
    
    for selector in highlight_selectors:
        elements = soup.select(selector)
        if elements:
            print(f"  Selector: {selector}")
            for elem in elements[:2]:
                text = elem.get_text().strip()[:100]
                print(f"    Text: {text}")
            print()
    
    # 4. Look for data attributes
    print("\n🏷️  DATA ATTRIBUTES:")
    data_attrs = soup.find_all(attrs={"data-value": True})
    for elem in data_attrs[:5]:
        print(f"  data-value: {elem.get('data-value')}")
        print(f"  Element: {elem.name} - {elem.get('class', [])}")
        print(f"  Text: {elem.get_text().strip()[:50]}")
        print()
    
    # 5. Find number patterns
    print("\n🔢 NUMERIC DATA:")
    numeric_elements = soup.find_all(text=re.compile(r'\d+\.?\d*[%]?'))
    numeric_dict = {}
    
    for elem in numeric_elements[:20]:  # Limit output
        text = elem.strip()
        if re.match(r'^\d+\.?\d*[%]?$', text):  # Pure numbers
            parent = elem.parent
            if parent:
                context = parent.get_text().strip()[:50]
                if text not in numeric_dict:
                    numeric_dict[text] = []
                numeric_dict[text].append(context)
    
    for number, contexts in list(numeric_dict.items())[:10]:
        print(f"  Number: {number}")
        for context in contexts[:2]:
            print(f"    Context: {context}")
        print()
    
    # 6. Find navigation/tab elements
    print("\n📑 NAVIGATION/TABS:")
    nav_selectors = [
        '.tab', '.nav', '.menu', '.segment', '.filter',
        '[role="tab"]', '[role="navigation"]'
    ]
    
    for selector in nav_selectors:
        elements = soup.select(selector)
        if elements:
            print(f"  Selector: {selector}")
            for elem in elements[:3]:
                text = elem.get_text().strip()[:50]
                print(f"    Text: {text}")
            print()

def find_specific_selectors(html_content: str):
    """Find specific selectors for key data points"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    print("\n" + "="*60)
    print("SPECIFIC SELECTOR RECOMMENDATIONS")
    print("="*60)
    
    # Peak rank search
    print("\n🎯 PEAK RANK SELECTORS:")
    peak_candidates = soup.find_all(text=re.compile(r'peak|highest|best', re.I))
    for candidate in peak_candidates[:5]:
        parent = candidate.parent
        if parent:
            # Look for nearby rank text
            siblings = parent.find_next_siblings()[:3]
            for sibling in siblings:
                if sibling and 'immortal' in sibling.get_text().lower():
                    print(f"  Found peak near: {candidate.strip()}")
                    print(f"  Parent: {parent.name} - {parent.get('class', [])}")
                    print(f"  Sibling: {sibling.name} - {sibling.get('class', [])}")
                    print(f"  Sibling text: {sibling.get_text().strip()}")
                    print()
    
    # Win/Loss data
    print("\n🏁 WIN/LOSS SELECTORS:")
    win_candidates = soup.find_all(text=re.compile(r'\d+W|\d+L|wins|losses|matches', re.I))
    for candidate in win_candidates[:5]:
        parent = candidate.parent
        if parent:
            print(f"  Text: {candidate.strip()}")
            print(f"  Parent: {parent.name} - {parent.get('class', [])}")
            print(f"  Full context: {parent.get_text().strip()[:100]}")
            print()

def main():
    """Main analysis function"""
    try:
        with open('sample.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        logger.info("Sample HTML file loaded successfully")
        
        # Run analyses
        analyze_html_structure(html_content)
        find_specific_selectors(html_content)
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        
    except FileNotFoundError:
        logger.error("sample.html file not found.")
    except Exception as e:
        logger.error(f"Error during analysis: {e}")

if __name__ == "__main__":
    main() 