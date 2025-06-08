import asyncio
import json
import re
from urllib.parse import quote
from flaresolverr_client import fetch_page_with_flaresolverr


def extract_initial_state(html_content: str):
    """
    Extract the window.__INITIAL_STATE__ JSON data from HTML.
    """
    try:
        # Look for window.__INITIAL_STATE__ = {...}; pattern
        # Use a more specific pattern to avoid capturing too much
        pattern = r'window\.__INITIAL_STATE__\s*=\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\});'
        match = re.search(pattern, html_content, re.DOTALL)
        
        if not match:
            # Try alternative patterns
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});[\s\n]*window\.',
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});[\s\n]*</script>',
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});[\s\n]*[a-zA-Z_]',
            ]
            
            for alt_pattern in patterns:
                match = re.search(alt_pattern, html_content, re.DOTALL)
                if match:
                    break
        
        if match:
            json_str = match.group(1)
            print(f"📄 Found JSON string ({len(json_str)} chars)")
            
            try:
                data = json.loads(json_str)
                return data
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing JSON: {e}")
                print(f"JSON start: {json_str[:100]}...")
                print(f"JSON end: ...{json_str[-100:]}")
                
                # Try to fix common JSON issues
                try:
                    # Remove potential trailing content
                    json_str_clean = json_str.rstrip()
                    if json_str_clean.endswith(','):
                        json_str_clean = json_str_clean[:-1]
                    
                    data = json.loads(json_str_clean)
                    print("✅ Fixed JSON by cleaning trailing content")
                    return data
                except json.JSONDecodeError:
                    print("❌ Could not fix JSON")
                    return None
        else:
            print("❌ Could not find window.__INITIAL_STATE__ pattern")
            return None
            
    except Exception as e:
        print(f"❌ Error extracting initial state: {e}")
        return None


def find_api_urls_in_html(html_content: str):
    """
    Find potential API URLs in the HTML content.
    """
    api_patterns = [
        r'https?://[^"\s]+/api/[^"\s]+',
        r'/api/[^"\s]+',
        r'https?://[^"\s]*tracker[^"\s]*/[^"\s]+',
        r'https?://api\.[^"\s]+',
        r'https?://public-api\.[^"\s]+',
    ]
    
    found_urls = set()
    
    for pattern in api_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        found_urls.update(matches)
    
    return sorted(list(found_urls))


def find_premier_data_in_json(data, path=""):
    """
    Recursively search for premier-related data in JSON structure.
    """
    premier_data = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if key contains premier-related terms
            if any(term in key.lower() for term in ['premier', 'playlist', 'segment']):
                premier_data.append({
                    'path': current_path,
                    'key': key,
                    'value': value,
                    'type': type(value).__name__
                })
            
            # Recursively search in nested structures
            if isinstance(value, (dict, list)):
                premier_data.extend(find_premier_data_in_json(value, current_path))
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            if isinstance(item, (dict, list)):
                premier_data.extend(find_premier_data_in_json(item, current_path))
    
    return premier_data


def analyze_network_patterns(html_content: str):
    """
    Analyze the HTML for network request patterns and endpoints.
    """
    print("🔍 Analyzing HTML for network patterns...")
    
    # Look for fetch/axios calls
    fetch_patterns = [
        r'fetch\s*\(\s*["\']([^"\']+)["\']',
        r'axios\.[get|post|put|delete]+\s*\(\s*["\']([^"\']+)["\']',
        r'\.get\s*\(\s*["\']([^"\']+)["\']',
        r'\.post\s*\(\s*["\']([^"\']+)["\']',
    ]
    
    network_calls = set()
    for pattern in fetch_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        network_calls.update(matches)
    
    # Look for URL building patterns
    url_building_patterns = [
        r'["\']https?://[^"\']+/api/[^"\']+["\']',
        r'["\']\/api\/[^"\']+["\']',
        r'baseURL\s*:\s*["\']([^"\']+)["\']',
        r'apiUrl\s*:\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in url_building_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        network_calls.update([m.strip('\'"') for m in matches])
    
    return sorted(list(network_calls))


async def analyze_profile_data(username: str):
    """
    Fetch profile page and analyze embedded data and API patterns.
    """
    print(f"🔬 Analyzing profile data for: {username}")
    print("=" * 60)
    
    encoded_username = quote(username)
    profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_username}"
    
    print(f"📍 Fetching: {profile_url}")
    
    try:
        html_content = await fetch_page_with_flaresolverr(profile_url)
        
        if not html_content:
            print("❌ No HTML content received")
            return
        
        print(f"✅ Received HTML content ({len(html_content)} chars)")
        
        # Extract initial state JSON
        print("\n🔍 Extracting window.__INITIAL_STATE__...")
        initial_state = extract_initial_state(html_content)
        premier_data = []  # Initialize to avoid UnboundLocalError
        
        # If JSON extraction fails, try manual line extraction
        if not initial_state:
            print("\n🔍 Trying manual line extraction...")
            lines = html_content.split('\n')
            for i, line in enumerate(lines):
                if 'window.__INITIAL_STATE__' in line:
                    print(f"📍 Found window.__INITIAL_STATE__ at line {i+1}")
                    print(f"📄 Line content: {line[:200]}...")
                    
                    # Try to extract just the relevant part
                    start_pos = line.find('{')
                    if start_pos != -1:
                        # Find potential end positions
                        potential_json = line[start_pos:]
                        print(f"📄 Potential JSON start: {potential_json[:150]}...")
                    break
        
        if initial_state:
            print("✅ Successfully extracted initial state JSON")
            print(f"📊 Top-level keys: {list(initial_state.keys())}")
            
            # Search for premier-related data
            print("\n🎯 Searching for premier-related data...")
            premier_data = find_premier_data_in_json(initial_state)
            
            if premier_data:
                print(f"✅ Found {len(premier_data)} premier-related entries:")
                for item in premier_data[:10]:  # Show first 10
                    print(f"  📍 {item['path']}: {item['type']}")
                    if item['type'] in ['str', 'int', 'float'] and len(str(item['value'])) < 100:
                        print(f"      Value: {item['value']}")
            else:
                print("❌ No premier-related data found in initial state")
        else:
            print("❌ Could not extract initial state JSON")
        
        # Find API URLs in HTML
        print("\n🌐 Searching for API URLs in HTML...")
        api_urls = find_api_urls_in_html(html_content)
        
        if api_urls:
            print(f"✅ Found {len(api_urls)} potential API URLs:")
            for url in api_urls:
                print(f"  🔗 {url}")
        else:
            print("❌ No API URLs found in HTML")
        
        # Analyze network patterns
        print("\n📡 Analyzing network request patterns...")
        network_calls = analyze_network_patterns(html_content)
        
        if network_calls:
            print(f"✅ Found {len(network_calls)} potential network calls:")
            for call in network_calls:
                print(f"  📞 {call}")
        else:
            print("❌ No network call patterns found")
        
        # Save the data for further analysis
        output_data = {
            'username': username,
            'profile_url': profile_url,
            'initial_state': initial_state,
            'api_urls': api_urls,
            'network_calls': network_calls,
            'premier_data': premier_data
        }
        
        with open(f"analysis_{username.replace('#', '_')}.json", 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        print(f"\n💾 Analysis saved to: analysis_{username.replace('#', '_')}.json")
        
        return output_data
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return None


async def main():
    """Main function to run the analysis."""
    print("🕵️ Tracker.gg Network Analysis Tool")
    print("=" * 50)
    
    username = "apolloZ#sun"
    
    print(f"Target username: {username}")
    print("This tool will:")
    print("1. Fetch the profile page HTML")
    print("2. Extract embedded JSON data")
    print("3. Search for API endpoints")
    print("4. Analyze network request patterns")
    print("5. Look for premier-specific data")
    print()
    
    result = await analyze_profile_data(username)
    
    if result and result.get('premier_data'):
        print("\n🎉 SUCCESS: Found premier-related data!")
        print("Next steps:")
        print("1. Check the saved JSON file for detailed data")
        print("2. Look for API endpoints that contain premier data")
        print("3. Test those endpoints with proper headers/cookies")
    else:
        print("\n⚠️  No premier data found in embedded JSON")
        print("Next steps:")
        print("1. Use browser dev tools to inspect network requests")
        print("2. Look for XHR/Fetch calls when page loads")
        print("3. Copy the working API calls with headers")


if __name__ == "__main__":
    asyncio.run(main()) 