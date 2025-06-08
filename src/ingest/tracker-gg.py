import asyncio
import json
import aiohttp
from urllib.parse import quote
from dotenv import load_dotenv
import os
import time
import random
from itertools import product
from pathlib import Path

# Import database loading functionality
from .data_loader import UnifiedTrackerDataLoader
from ..shared.utils import setup_logger

load_dotenv()

logger = setup_logger(__name__)

FLARESOLVERR_URL = "http://tracker-flaresolverr:8191/v1"

# Timing configuration to avoid blocks and rate limiting
# Adjust these values based on your needs vs. speed preferences
TIMING_CONFIG = {
    "min_request_delay": 1.0,      # Minimum delay between requests (seconds)
    "max_request_delay": 3.0,      # Maximum delay between requests (seconds)
    "batch_size": 10,              # Process endpoints in batches (smaller = more cautious)
    "batch_delay": 15.0,           # Delay between batches (seconds)
    "authentication_wait": 8.0,    # Wait after profile load for full auth (seconds)
    "retry_base_delay": 2.0,       # Base delay for exponential backoff (seconds)
    "retry_max_delay": 30.0,       # Maximum retry delay (seconds)
    "max_retries": 3,              # Maximum retry attempts per request
    "rate_limit_delay": 60.0,      # Delay when rate limited (seconds)
    "consecutive_failure_threshold": 5,  # Trigger extra delay after N failures
    "extra_delay_base": 30.0,      # Base extra delay for consecutive failures (seconds)
}


def extract_json_from_html(html_content: str):
    """Extract JSON from HTML wrapper that flaresolverr returns."""
    try:
        import re
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
        print(f"❌ Error extracting JSON: {e}")
        return None


async def call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent, retry_count=0):
    """Call a specific API endpoint using the flaresolverr session with retry logic."""
    print(f"\n📡 {endpoint_name}")
    print(f"🔗 {endpoint_url}")
    
    # Add random delay before each request
    delay = random.uniform(TIMING_CONFIG["min_request_delay"], TIMING_CONFIG["max_request_delay"])
    print(f"⏳ Waiting {delay:.1f}s before request...")
    await asyncio.sleep(delay)
    
    payload = {
        "cmd": "request.get",
        "url": endpoint_url,
        "session": session_id,
        "headers": {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "dnt": "1",
            "origin": "https://tracker.gg",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://tracker.gg/",
            "sec-ch-ua": '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": user_agent
        },
        "maxTimeout": 30000
    }
    
    try:
        async with session.post(FLARESOLVERR_URL, json=payload) as response:
            result = await response.json()
            solution = result.get("solution", {})
            
            status = solution.get("status")
            content = solution.get("response", "")
            
            # Handle rate limiting and retry logic
            if status == 429 or (status == 403 and "rate" in content.lower()):
                print(f"🚫 Rate limited (status {status})")
                if retry_count < TIMING_CONFIG["max_retries"]:
                    retry_delay = min(
                        TIMING_CONFIG["retry_base_delay"] * (2 ** retry_count) + random.uniform(0, 5),
                        TIMING_CONFIG["retry_max_delay"]
                    )
                    print(f"⏳ Retrying in {retry_delay:.1f}s (attempt {retry_count + 1}/{TIMING_CONFIG['max_retries']})")
                    await asyncio.sleep(retry_delay)
                    return await call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent, retry_count + 1)
                else:
                    print(f"❌ Max retries exceeded for rate limiting")
                    return {"endpoint": endpoint_name, "url": endpoint_url, "status": "rate_limited", "status_code": status}
            
            if status == 200:
                print("✅ Success!")
                json_data = extract_json_from_html(content)
                if json_data:
                    # Create safe filename
                    safe_name = endpoint_name.replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')
                    filename = f"grammar_{safe_name}.json"
                    
                    with open(filename, 'w') as f:
                        json.dump(json_data, f, indent=2)
                    
                    print(f"💾 Saved: {filename}")
                    
                    # Show data info
                    if isinstance(json_data, dict):
                        if 'data' in json_data and isinstance(json_data['data'], list):
                            print(f"📊 Items: {len(json_data['data'])}")
                        else:
                            print(f"📄 Keys: {list(json_data.keys())}")
                    
                    return {
                        "endpoint": endpoint_name,
                        "url": endpoint_url,
                        "status": "success",
                        "filename": filename,
                        "data_size": len(json_data.get('data', [])) if isinstance(json_data, dict) and 'data' in json_data else 0
                    }
                else:
                    print(f"⚠️  No JSON: {content[:100]}...")
                    return {"endpoint": endpoint_name, "url": endpoint_url, "status": "no_json"}
            else:
                print(f"❌ Status {status}: {content[:100]}...")
                # Retry on server errors
                if status >= 500 and retry_count < TIMING_CONFIG["max_retries"]:
                    retry_delay = TIMING_CONFIG["retry_base_delay"] * (2 ** retry_count)
                    print(f"⏳ Server error, retrying in {retry_delay:.1f}s...")
                    await asyncio.sleep(retry_delay)
                    return await call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent, retry_count + 1)
                return {"endpoint": endpoint_name, "url": endpoint_url, "status": "failed", "status_code": status}
                
    except Exception as e:
        print(f"❌ Error: {e}")
        # Retry on connection errors
        if retry_count < TIMING_CONFIG["max_retries"]:
            retry_delay = TIMING_CONFIG["retry_base_delay"] * (2 ** retry_count)
            print(f"⏳ Connection error, retrying in {retry_delay:.1f}s...")
            await asyncio.sleep(retry_delay)
            return await call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent, retry_count + 1)
        return {"endpoint": endpoint_name, "url": endpoint_url, "status": "error", "error": str(e)}


async def generate_all_api_endpoints(username: str):
    """Generate all possible API endpoints based on the grammar."""
    
    encoded_username = quote(username)
    base_url = "https://api.tracker.gg"
    
    # Define all possible values from the grammar
    playlists = [
        "competitive", "premier", "unrated", "deathmatch", "team-deathmatch", 
        "spikerush", "swiftplay", "escalation", "replication", "snowball",
        "newmap-swiftplay", "newmap-bomb"
    ]
    
    segments = ["loadout", "month-report", "playlist", "season-report"]
    
    stats = ["kills", "deaths", "assists", "damage", "headshots", "score"]
    
    platforms = ["pc"]
    types = ["competitive", "unrated"]
    filters = ["encounters"]
    sources = ["web", "ios"]
    
    # Current season ID (empty for current)
    season_ids = ["", "97b6e739-44cc-ffa7-49ad-398ba502ceb0"]  # Empty + example season
    
    offsets = ["0", "180", "-300"]  # Different timezone offsets
    
    endpoints = []
    
    # API v1 - Aggregated matches
    print("🔧 Generating v1 endpoints...")
    for playlist, season_id, offset in product(playlists, season_ids, offsets):
        url = f"{base_url}/api/v1/valorant/matches/riot/{encoded_username}/aggregated"
        params = f"?localOffset={offset}&playlist={playlist}&seasonId={season_id}"
        name = f"v1_aggregated_{playlist}_{season_id or 'current'}_{offset}"
        endpoints.append((name, url + params))
    
    # API v2 - Matches feed
    print("🔧 Generating v2 matches endpoints...")
    for platform, type_val in product(platforms, types):
        url = f"{base_url}/api/v2/valorant/standard/matches/riot/{encoded_username}"
        params = f"?platform={platform}&type={type_val}"
        name = f"v2_matches_{platform}_{type_val}"
        endpoints.append((name, url + params))
    
    # API v2 - Profile aggregates
    print("🔧 Generating v2 profile aggregates...")
    for offset, filter_val, platform, playlist in product(offsets, filters, platforms, playlists):
        url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}/aggregated"
        params = f"?localOffset={offset}&filter={filter_val}&platform={platform}&playlist={playlist}"
        name = f"v2_aggregated_{filter_val}_{platform}_{playlist}_{offset}"
        endpoints.append((name, url + params))
    
    # API v2 - Profile segments
    print("🔧 Generating v2 profile segments...")
    for segment, playlist in product(segments, playlists):
        url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/{segment}"
        
        if segment == "loadout":
            # Loadout: playlist mandatory, seasonId optional
            for season_id in season_ids:
                params = f"?playlist={playlist}&seasonId={season_id}" if season_id else f"?playlist={playlist}"
                name = f"v2_segment_{segment}_{playlist}_{season_id or 'current'}"
                endpoints.append((name, url + params))
        elif segment == "playlist":
            # Playlist: playlist and source mandatory
            for source in sources:
                params = f"?playlist={playlist}&source={source}"
                name = f"v2_segment_{segment}_{playlist}_{source}"
                endpoints.append((name, url + params))
        else:
            # month-report, season-report: only playlist mandatory
            params = f"?playlist={playlist}"
            name = f"v2_segment_{segment}_{playlist}"
            endpoints.append((name, url + params))
    
    # API v2 - Profile playlist-level stats
    print("🔧 Generating v2 stats endpoints...")
    for stat, playlist in product(stats, playlists):
        url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}/stats/playlist/{stat}"
        params = f"?playlist={playlist}"
        name = f"v2_stats_{stat}_{playlist}"
        endpoints.append((name, url + params))
    
    # API v2 - Raw profile (no query params)
    url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}"
    name = "v2_profile_raw"
    endpoints.append((name, url))
    
    print(f"📊 Generated {len(endpoints)} total endpoints")
    return endpoints


async def test_complete_api_grammar(username: str):
    """Test all API endpoints from the grammar using flaresolverr."""
    
    session_id = f"grammar_test_{username.replace('#', '_')}_{int(time.time())}"
    encoded_username = quote(username)
    profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_username}"
    
    print("🔬 Complete API Grammar Test")
    print("=" * 60)
    print(f"👤 Target: {username}")
    print(f"🔧 FlareSolverr: {FLARESOLVERR_URL}")
    print(f"🎯 Session: {session_id}")
    print(f"⏱️  Timing: {TIMING_CONFIG['min_request_delay']}-{TIMING_CONFIG['max_request_delay']}s delays, {TIMING_CONFIG['batch_size']} batch size")
    print()
    
    # Generate all endpoints
    endpoints = await generate_all_api_endpoints(username)
    print(f"🚀 Will test {len(endpoints)} endpoints in batches of {TIMING_CONFIG['batch_size']}")
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Create flaresolverr session
            print("\n📋 Step 1: Creating browser session...")
            create_payload = {"cmd": "sessions.create", "session": session_id}
            
            async with session.post(FLARESOLVERR_URL, json=create_payload) as response:
                result = await response.json()
                if result.get("status") != "ok":
                    print(f"❌ Failed to create session: {result}")
                    return None
                print("✅ Session created")
            
            # Step 2: Load profile page to establish authentication
            print("\n📋 Step 2: Loading profile page for authentication...")
            navigate_payload = {
                "cmd": "request.get",
                "url": profile_url,
                "session": session_id,
                "maxTimeout": 60000,
                "returnOnlyCookies": False,
                "returnRawHtml": True
            }
            
            async with session.post(FLARESOLVERR_URL, json=navigate_payload) as response:
                result = await response.json()
                solution = result.get("solution", {})
                
                if result.get("status") != "ok" or solution.get("status") != 200:
                    print(f"❌ Failed to load profile: {result}")
                    return None
                
                print("✅ Profile loaded - authentication established")
                print(f"🍪 Cookies: {len(solution.get('cookies', []))}")
                user_agent = solution.get("userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Step 3: Wait for full page load and authentication
            print(f"\n📋 Step 3: Waiting {TIMING_CONFIG['authentication_wait']}s for complete page load and authentication...")
            await asyncio.sleep(TIMING_CONFIG['authentication_wait'])
            
            # Step 4: Test all endpoints systematically in batches
            print("\n📋 Step 4: Testing all API endpoints in batches...")
            print("=" * 50)
            
            successful = 0
            failed = 0
            consecutive_failures = 0
            total_batches = (len(endpoints) + TIMING_CONFIG['batch_size'] - 1) // TIMING_CONFIG['batch_size']
            
            for batch_num in range(total_batches):
                start_idx = batch_num * TIMING_CONFIG['batch_size']
                end_idx = min(start_idx + TIMING_CONFIG['batch_size'], len(endpoints))
                batch_endpoints = endpoints[start_idx:end_idx]
                
                print(f"\n🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_endpoints)} endpoints)")
                print(f"📊 Overall progress: {start_idx}/{len(endpoints)} ({(start_idx/len(endpoints)*100):.1f}%)")
                
                for i, (endpoint_name, endpoint_url) in enumerate(batch_endpoints):
                    global_index = start_idx + i
                    print(f"\n[{global_index+1}/{len(endpoints)}] Batch progress: {i+1}/{len(batch_endpoints)}")
                    
                    result = await call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent)
                    results.append(result)
                    
                    if result.get("status") == "success":
                        successful += 1
                        consecutive_failures = 0  # Reset on success
                    else:
                        failed += 1
                        consecutive_failures += 1
                        
                        # Handle consecutive failures - possible blocking
                        if consecutive_failures >= TIMING_CONFIG["consecutive_failure_threshold"]:
                            extra_delay = min(
                                TIMING_CONFIG["extra_delay_base"] + consecutive_failures * 5, 
                                120  # Cap at 2 minutes
                            )
                            print(f"⚠️  {consecutive_failures} consecutive failures detected!")
                            print(f"⏳ Taking extra break of {extra_delay}s to avoid blocks...")
                            await asyncio.sleep(extra_delay)
                            consecutive_failures = 0  # Reset after break
                
                # Batch completion summary
                print(f"\n✅ Batch {batch_num + 1} completed: {successful} successful, {failed} failed")
                
                # Inter-batch delay (except for the last batch)
                if batch_num < total_batches - 1:
                    print(f"⏳ Waiting {TIMING_CONFIG['batch_delay']}s before next batch...")
                    await asyncio.sleep(TIMING_CONFIG['batch_delay'])
            
            # Step 5: Save complete summary
            print("\n📋 Step 5: Saving complete results...")
            summary = {
                "username": username,
                "session_id": session_id,
                "timestamp": time.time(),
                "total_endpoints": len(endpoints),
                "successful_endpoints": successful,
                "failed_endpoints": failed,
                "success_rate": f"{(successful/len(endpoints)*100):.1f}%",
                "timing_config": TIMING_CONFIG,
                "total_batches": total_batches,
                "results": results
            }
            
            with open(f"complete_grammar_test_{username.replace('#', '_')}.json", 'w') as f:
                json.dump(summary, f, indent=2)
            
            print("💾 Complete summary saved")
            return summary
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
        
        finally:
            # Cleanup with delay
            try:
                print("\n📋 Step 6: Cleaning up session...")
                await asyncio.sleep(2)  # Give time before cleanup
                destroy_payload = {"cmd": "sessions.destroy", "session": session_id}
                async with session.post(FLARESOLVERR_URL, json=destroy_payload) as response:
                    result = await response.json()
                    if result.get("status") == "ok":
                        print("✅ Session cleaned up")
            except Exception as e:
                print(f"⚠️  Cleanup error: {e}")


async def main():
    """Main function to run the complete grammar test."""
    
    username = "apolloZ#sun"
    
    print("🧬 Testing Complete Tracker.gg API Grammar")
    print("This will systematically test ALL possible endpoint combinations")
    print("from the provided grammar rules.\n")
    
    # Calculate estimated time
    endpoints = await generate_all_api_endpoints(username)
    avg_delay = (TIMING_CONFIG['min_request_delay'] + TIMING_CONFIG['max_request_delay']) / 2
    batches = (len(endpoints) + TIMING_CONFIG['batch_size'] - 1) // TIMING_CONFIG['batch_size']
    estimated_time = (
        len(endpoints) * avg_delay +  # Request delays
        (batches - 1) * TIMING_CONFIG['batch_delay'] +  # Inter-batch delays
        TIMING_CONFIG['authentication_wait'] +  # Initial auth wait
        30  # Session setup and cleanup buffer
    ) / 60  # Convert to minutes
    
    print(f"⏱️  Estimated completion time: {estimated_time:.1f} minutes")
    print(f"📊 {len(endpoints)} endpoints in {batches} batches")
    print("💡 Tip: This will respect rate limits and use human-like timing\n")
    
    start_time = time.time()
    
    # Run the complete grammar test
    summary = await test_complete_api_grammar(username)
    
    actual_time = (time.time() - start_time) / 60
    
    if summary:
        print("\n🎉 COMPLETE GRAMMAR TEST FINISHED!")
        print("=" * 60)
        print(f"📊 Total endpoints: {summary['total_endpoints']}")
        print(f"✅ Successful: {summary['successful_endpoints']}")
        print(f"❌ Failed: {summary['failed_endpoints']}")
        print(f"📈 Success rate: {summary['success_rate']}")
        print(f"⏱️  Actual time: {actual_time:.1f} minutes")
        print(f"🎯 Efficiency: {(estimated_time/actual_time*100):.0f}% of estimate" if actual_time > 0 else "")
        
        print(f"\n📁 Data files created:")
        successful_files = [r.get('filename') for r in summary['results'] if r.get('filename')]
        for filename in successful_files[:10]:  # Show first 10
            print(f"  📄 {filename}")
        
        if len(successful_files) > 10:
            print(f"  ... and {len(successful_files) - 10} more files")
        
        print(f"\n📋 Complete summary: complete_grammar_test_{username.replace('#', '_')}.json")
        
        # Show breakdown by API version
        v1_success = len([r for r in summary['results'] if r.get('endpoint', '').startswith('v1_') and r.get('status') == 'success'])
        v2_success = len([r for r in summary['results'] if r.get('endpoint', '').startswith('v2_') and r.get('status') == 'success'])
        rate_limited = len([r for r in summary['results'] if r.get('status') == 'rate_limited'])
        
        print(f"\n📊 Breakdown:")
        print(f"  🔹 API v1 successful: {v1_success}")
        print(f"  🔹 API v2 successful: {v2_success}")
        if rate_limited > 0:
            print(f"  🚫 Rate limited: {rate_limited}")
        
    else:
        print("❌ Grammar test failed")
    
    print("\n✨ Complete API discovery finished!")


if __name__ == "__main__":
    asyncio.run(main()) 