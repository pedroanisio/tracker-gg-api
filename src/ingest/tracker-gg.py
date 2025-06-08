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

# Endpoint priorities for targeted updates (higher = more important)
ENDPOINT_PRIORITIES = {
    "v1_competitive_aggregated": 1.0,
    "v1_premier_aggregated": 0.9,
    "v2_competitive_playlist": 0.8,
    "v2_premier_playlist": 0.7,
    "v1_unrated_aggregated": 0.6,
    "v2_unrated_playlist": 0.5,
    "v2_deathmatch_playlist": 0.4,
    "v2_loadout_segments": 0.3,
    "v2_swiftplay_playlist": 0.2,
    "v2_spikerush_playlist": 0.1
}

# Priority thresholds
PRIORITY_HIGH = 0.7  # For critical updates
PRIORITY_MEDIUM = 0.4  # For regular updates
PRIORITY_LOW = 0.1   # For full updates only


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


def organize_results_for_database(username: str, results: list) -> dict:
    """Organize endpoint results into a format compatible with the database loader."""
    
    # Extract the riot_id from username 
    riot_id = username  # Assuming username is already in riot_id format (username#tag)
    
    # Group successful results by endpoint
    endpoints_data = {}
    
    for result in results:
        if result.get("status") == "success" and result.get("filename"):
            endpoint_name = result["endpoint"]
            
            try:
                # Load the saved JSON file
                with open(result["filename"], 'r') as f:
                    endpoint_data = json.load(f)
                
                # Determine endpoint type and playlist from name
                endpoint_type = ""
                playlist = ""
                
                if "v1_aggregated" in endpoint_name:
                    endpoint_type = "v1_aggregated"
                    # Extract playlist from endpoint name (e.g., v1_aggregated_competitive_current_0)
                    parts = endpoint_name.split('_')
                    if len(parts) >= 3:
                        playlist = parts[2]
                elif "v2_segment_playlist" in endpoint_name:
                    endpoint_type = "v2_playlist"
                    # Extract playlist (e.g., v2_segment_playlist_competitive_web)
                    parts = endpoint_name.split('_')
                    if len(parts) >= 4:
                        playlist = parts[3]
                elif "v2_segment_loadout" in endpoint_name:
                    endpoint_type = "v2_loadout"
                    # Extract playlist (e.g., v2_segment_loadout_competitive_current)
                    parts = endpoint_name.split('_')
                    if len(parts) >= 4:
                        playlist = parts[3]
                
                # Create the endpoint entry
                endpoints_data[endpoint_name] = {
                    "status": "success",
                    "data": endpoint_data,
                    "endpoint_type": endpoint_type,
                    "playlist": playlist,
                    "url": result["url"],
                    "timestamp": time.time()
                }
                
                logger.info(f"Organized endpoint {endpoint_name} for database loading")
                
            except Exception as e:
                logger.error(f"Failed to load data from {result['filename']}: {e}")
                continue
    
    # Create the combined data structure in browser intercepted format
    combined_data = {
        "riot_id": riot_id,
        "capture_method": "browser_interception",
        "capture_timestamp": time.time(),
        "endpoints": endpoints_data,
        "metadata": {
            "total_endpoints_attempted": len(results),
            "successful_endpoints": len(endpoints_data),
            "scraper_version": "tracker-gg-grammar-test",
            "timing_config": TIMING_CONFIG
        }
    }
    
    logger.info(f"Organized {len(endpoints_data)} successful endpoints for database loading")
    return combined_data


def load_results_to_database(username: str, combined_data: dict, data_dir: str = "./data") -> dict:
    """Load the organized results into the database using UnifiedTrackerDataLoader."""
    
    try:
        # Ensure data directory exists
        data_path = Path(data_dir)
        data_path.mkdir(exist_ok=True)
        
        # Save the combined data to a file in the expected format
        timestamp = int(time.time())
        safe_username = username.replace('#', '_')
        combined_filename = data_path / f"browser_capture_{safe_username}_{timestamp}.json"
        
        with open(combined_filename, 'w') as f:
            json.dump(combined_data, f, indent=2)
        
        logger.info(f"Saved combined data to {combined_filename}")
        
        # Load into database using the convenience function
        logger.info("Loading data into database...")
        from .data_loader import load_single_file
        stats = load_single_file(str(combined_filename))
        
        logger.info(f"Database loading completed: {stats}")
        
        return {
            "status": "success",
            "combined_filename": str(combined_filename),
            "loading_stats": stats,
            "endpoints_loaded": len(combined_data.get("endpoints", {}))
        }
        
    except Exception as e:
        logger.error(f"Failed to load data to database: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


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


async def test_complete_api_grammar(username: str, load_to_database: bool = True):
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
            
            # Step 6: Load successful results into database
            if load_to_database and successful > 0:
                print("\n📋 Step 6: Loading data into database...")
                try:
                    # Organize results for database loading
                    combined_data = organize_results_for_database(username, results)
                    
                    if combined_data.get("endpoints"):
                        # Load into database
                        db_result = load_results_to_database(username, combined_data)
                        
                        if db_result.get("status") == "success":
                            print("✅ Database loading successful!")
                            print(f"📊 Loaded {db_result['endpoints_loaded']} endpoints into database")
                            print(f"📁 Combined data saved: {db_result['combined_filename']}")
                            
                            # Add database info to summary
                            summary["database_loading"] = db_result
                        else:
                            print(f"❌ Database loading failed: {db_result.get('error', 'Unknown error')}")
                            summary["database_loading"] = db_result
                    else:
                        print("⚠️  No successful endpoints to load into database")
                        summary["database_loading"] = {"status": "no_data", "message": "No successful endpoints"}
                        
                except Exception as e:
                    print(f"❌ Database loading error: {e}")
                    logger.error(f"Database loading failed: {e}")
                    summary["database_loading"] = {"status": "error", "error": str(e)}
            elif load_to_database and successful == 0:
                print("\n⚠️  Skipping database loading - no successful endpoints")
                summary["database_loading"] = {"status": "skipped", "reason": "no_successful_endpoints"}
            else:
                print("\n📋 Step 6: Database loading disabled")
                summary["database_loading"] = {"status": "disabled"}
            
            return summary
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
        
        finally:
            # Cleanup with delay
            try:
                print("\n📋 Step 7: Cleaning up session...")
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
    
    # Run the complete grammar test (with database loading enabled by default)
    summary = await test_complete_api_grammar(username, load_to_database=True)
    
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
        
        # Show database loading results
        db_loading = summary.get("database_loading", {})
        db_status = db_loading.get("status", "unknown")
        
        print(f"\n🗄️  Database Loading:")
        if db_status == "success":
            print(f"  ✅ Successfully loaded {db_loading.get('endpoints_loaded', 0)} endpoints")
            print(f"  📁 Combined file: {Path(db_loading.get('combined_filename', '')).name}")
        elif db_status == "error":
            print(f"  ❌ Failed: {db_loading.get('error', 'Unknown error')}")
        elif db_status == "skipped":
            print(f"  ⚠️  Skipped: {db_loading.get('reason', 'No reason given')}")
        elif db_status == "disabled":
            print(f"  ⏸️  Disabled")
        elif db_status == "no_data":
            print(f"  📭 No data to load")
        else:
            print(f"  ❓ Status: {db_status}")
        
    else:
        print("❌ Grammar test failed")
    
    print("\n✨ Complete API discovery finished!")


def load_existing_files_to_database(data_dir: str = "./data", pattern: str = "grammar_*.json") -> dict:
    """Load existing grammar test files into the database."""
    
    try:
        from .data_loader import load_data_from_directory
        
        data_path = Path(data_dir)
        if not data_path.exists():
            return {"status": "error", "error": f"Directory {data_dir} does not exist"}
        
        # Find grammar files
        grammar_files = list(data_path.glob(pattern))
        
        if not grammar_files:
            return {"status": "error", "error": f"No files matching pattern '{pattern}' found in {data_dir}"}
        
        logger.info(f"Found {len(grammar_files)} grammar files to process")
        
        # Load all files
        stats = load_data_from_directory(data_dir)
        
        return {
            "status": "success",
            "files_found": len(grammar_files),
            "loading_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to load existing files: {e}")
        return {"status": "error", "error": str(e)}


async def load_full_api_data(username: str, load_to_database: bool = True) -> dict:
    """
    Load complete API data by testing ALL possible endpoints.
    Use this for initial data discovery or comprehensive updates.
    
    Args:
        username: Riot ID (username#tag)
        load_to_database: Whether to load results into database
        
    Returns:
        Complete API discovery results
    """
    
    print("🔍 FULL API DATA LOADING")
    print("=" * 50)
    print("📊 This will test ALL possible endpoint combinations")
    print("🔧 Use for: Initial discovery, comprehensive updates, data mining")
    print("⏱️  Expected time: 15-30 minutes depending on rate limits")
    print()
    
    return await test_complete_api_grammar(username, load_to_database)


async def update_recent_data(username: str, priority_threshold: float = PRIORITY_HIGH, load_to_database: bool = True) -> dict:
    """
    Update only the most recent/important data endpoints.
    Much faster than full API loading, focuses on priority endpoints.
    
    Args:
        username: Riot ID (username#tag)
        priority_threshold: Minimum priority level (0.0-1.0)
        load_to_database: Whether to load results into database
        
    Returns:
        Targeted update results
    """
    
    session_id = f"recent_update_{username.replace('#', '_')}_{int(time.time())}"
    encoded_username = quote(username)
    profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_username}"
    
    print("⚡ RECENT DATA UPDATE")
    print("=" * 50)
    print(f"👤 Target: {username}")
    print(f"🎯 Priority threshold: {priority_threshold}")
    print(f"🔧 Session: {session_id}")
    print("📊 This will test only HIGH-PRIORITY endpoints for recent data")
    print("🔧 Use for: Regular updates, recent match data, current stats")
    print("⏱️  Expected time: 2-5 minutes")
    print()
    
    # Generate only priority endpoints
    priority_endpoints = await generate_priority_endpoints(username, priority_threshold)
    print(f"🎯 Selected {len(priority_endpoints)} priority endpoints (threshold ≥ {priority_threshold})")
    
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
                    return create_error_result(username, "Failed to create session")
                print("✅ Session created")
            
            # Step 2: Load profile page for authentication
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
                    return create_error_result(username, "Failed to load profile")
                
                print("✅ Profile loaded - authentication established")
                user_agent = solution.get("userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Step 3: Quick authentication wait (shorter than full discovery)
            auth_wait = 3.0  # Reduced wait time for updates
            print(f"\n📋 Step 3: Waiting {auth_wait}s for authentication...")
            await asyncio.sleep(auth_wait)
            
            # Step 4: Test priority endpoints efficiently
            print("\n📋 Step 4: Testing priority endpoints...")
            print("=" * 40)
            
            successful = 0
            failed = 0
            
            for i, (endpoint_name, endpoint_url) in enumerate(priority_endpoints):
                print(f"\n[{i+1}/{len(priority_endpoints)}] Priority endpoint:")
                
                result = await call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent)
                results.append(result)
                
                if result.get("status") == "success":
                    successful += 1
                else:
                    failed += 1
                
                # Shorter delays for priority updates
                if i < len(priority_endpoints) - 1:  # Not the last endpoint
                    delay = random.uniform(0.5, 1.5)  # Faster than full discovery
                    print(f"⏳ Quick delay: {delay:.1f}s...")
                    await asyncio.sleep(delay)
            
            # Step 5: Create results summary
            print("\n📋 Step 5: Creating update summary...")
            summary = {
                "username": username,
                "session_id": session_id,
                "update_type": "recent_data",
                "priority_threshold": priority_threshold,
                "timestamp": time.time(),
                "total_endpoints": len(priority_endpoints),
                "successful_endpoints": successful,
                "failed_endpoints": failed,
                "success_rate": f"{(successful/len(priority_endpoints)*100):.1f}%" if priority_endpoints else "0%",
                "timing_config": {
                    "update_mode": "priority_only",
                    "auth_wait": auth_wait,
                    "quick_delays": "0.5-1.5s"
                },
                "results": results
            }
            
            # Save summary
            summary_filename = f"recent_update_{username.replace('#', '_')}_{int(time.time())}.json"
            with open(summary_filename, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print("💾 Update summary saved")
            
            # Step 6: Load to database if requested
            if load_to_database and successful > 0:
                print("\n📋 Step 6: Loading recent data into database...")
                try:
                    combined_data = organize_results_for_database(username, results)
                    
                    if combined_data.get("endpoints"):
                        db_result = load_results_to_database(username, combined_data)
                        
                        if db_result.get("status") == "success":
                            print("✅ Database loading successful!")
                            print(f"📊 Loaded {db_result['endpoints_loaded']} priority endpoints")
                            summary["database_loading"] = db_result
                        else:
                            print(f"❌ Database loading failed: {db_result.get('error')}")
                            summary["database_loading"] = db_result
                    else:
                        print("⚠️  No data to load into database")
                        summary["database_loading"] = {"status": "no_data"}
                        
                except Exception as e:
                    print(f"❌ Database loading error: {e}")
                    summary["database_loading"] = {"status": "error", "error": str(e)}
            elif successful == 0:
                summary["database_loading"] = {"status": "skipped", "reason": "no_successful_endpoints"}
            else:
                summary["database_loading"] = {"status": "disabled"}
            
            return summary
            
        except Exception as e:
            print(f"❌ Update error: {e}")
            return create_error_result(username, str(e))
        
        finally:
            # Quick cleanup
            try:
                print("\n📋 Step 7: Cleaning up session...")
                destroy_payload = {"cmd": "sessions.destroy", "session": session_id}
                async with session.post(FLARESOLVERR_URL, json=destroy_payload) as response:
                    result = await response.json()
                    if result.get("status") == "ok":
                        print("✅ Session cleaned up")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")


async def generate_priority_endpoints(username: str, priority_threshold: float = PRIORITY_HIGH) -> list:
    """
    Generate only priority endpoints for targeted updates.
    
    Args:
        username: Riot ID
        priority_threshold: Minimum priority level (0.0-1.0)
        
    Returns:
        List of (endpoint_name, endpoint_url) tuples for priority endpoints
    """
    
    encoded_username = quote(username)
    base_url = "https://api.tracker.gg"
    
    # Define priority endpoint patterns
    priority_endpoints = []
    
    # High priority: Current competitive and premier data
    if priority_threshold <= 1.0:
        # V1 Aggregated - most recent data
        for playlist in ["competitive", "premier"]:
            url = f"{base_url}/api/v1/valorant/matches/riot/{encoded_username}/aggregated"
            params = f"?localOffset=0&playlist={playlist}&seasonId="  # Current season
            name = f"v1_aggregated_{playlist}_current_0"
            priority = ENDPOINT_PRIORITIES.get(f"v1_{playlist}_aggregated", 0.5)
            
            if priority >= priority_threshold:
                priority_endpoints.append((name, url + params, priority))
    
    if priority_threshold <= 0.8:
        # V2 Playlist segments - current competitive/premier data
        for playlist in ["competitive", "premier"]:
            url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist"
            params = f"?playlist={playlist}&source=web"
            name = f"v2_segment_playlist_{playlist}_web"
            priority = ENDPOINT_PRIORITIES.get(f"v2_{playlist}_playlist", 0.5)
            
            if priority >= priority_threshold:
                priority_endpoints.append((name, url + params, priority))
    
    if priority_threshold <= 0.6:
        # V1 Unrated for broader recent activity
        url = f"{base_url}/api/v1/valorant/matches/riot/{encoded_username}/aggregated"
        params = f"?localOffset=0&playlist=unrated&seasonId="
        name = f"v1_aggregated_unrated_current_0"
        priority = ENDPOINT_PRIORITIES.get("v1_unrated_aggregated", 0.5)
        
        if priority >= priority_threshold:
            priority_endpoints.append((name, url + params, priority))
    
    if priority_threshold <= 0.5:
        # V2 Unrated playlist
        url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist"
        params = f"?playlist=unrated&source=web"
        name = f"v2_segment_playlist_unrated_web"
        priority = ENDPOINT_PRIORITIES.get("v2_unrated_playlist", 0.5)
        
        if priority >= priority_threshold:
            priority_endpoints.append((name, url + params, priority))
    
    if priority_threshold <= 0.4:
        # Additional casual modes
        for playlist in ["deathmatch", "swiftplay"]:
            url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist"
            params = f"?playlist={playlist}&source=web"
            name = f"v2_segment_playlist_{playlist}_web"
            priority = ENDPOINT_PRIORITIES.get(f"v2_{playlist}_playlist", 0.3)
            
            if priority >= priority_threshold:
                priority_endpoints.append((name, url + params, priority))
    
    if priority_threshold <= 0.3:
        # Loadout data (less frequent updates needed)
        for playlist in ["competitive", "premier"]:
            url = f"{base_url}/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/loadout"
            params = f"?playlist={playlist}&seasonId="
            name = f"v2_segment_loadout_{playlist}_current"
            priority = ENDPOINT_PRIORITIES.get("v2_loadout_segments", 0.3)
            
            if priority >= priority_threshold:
                priority_endpoints.append((name, url + params, priority))
    
    # Sort by priority (highest first)
    priority_endpoints.sort(key=lambda x: x[2], reverse=True)
    
    # Return only name and URL (remove priority)
    return [(name, url) for name, url, priority in priority_endpoints]


def create_error_result(username: str, error_message: str) -> dict:
    """Create a standardized error result."""
    return {
        "username": username,
        "status": "error",
        "error": error_message,
        "timestamp": time.time(),
        "total_endpoints": 0,
        "successful_endpoints": 0,
        "failed_endpoints": 0,
        "success_rate": "0%"
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tracker.gg API Data Loader")
    parser.add_argument("--username", default="apolloZ#sun", help="Riot ID to process")
    parser.add_argument("--mode", choices=["init", "update", "full"], default="init", 
                       help="Operation mode: init=full load for new users, update=recent data only, full=complete discovery")
    parser.add_argument("--priority", choices=["high", "medium", "low"], default="high",
                       help="Priority level for update mode (high=0.7+, medium=0.4+, low=0.1+)")
    parser.add_argument("--no-database", action="store_true", help="Skip database loading")
    parser.add_argument("--load-existing", action="store_true", help="Load existing grammar files to database")
    parser.add_argument("--data-dir", default="./data", help="Data directory for database files")
    
    args = parser.parse_args()
    
    if args.load_existing:
        print("📁 Loading existing grammar files to database...")
        result = load_existing_files_to_database(args.data_dir)
        
        if result["status"] == "success":
            print(f"✅ Successfully processed {result['files_found']} files")
            print(f"📊 Loading stats: {result['loading_stats']}")
        else:
            print(f"❌ Failed: {result['error']}")
    else:
        # Run the normal grammar test
        async def main_with_args():
            username = args.username
            load_to_db = not args.no_database
            
            print("🧬 Testing Complete Tracker.gg API Grammar")
            if load_to_db:
                print("🗄️  Database loading: ENABLED")
            else:
                print("🗄️  Database loading: DISABLED")
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
            summary = await test_complete_api_grammar(username, load_to_database=load_to_db)
            
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
                
                # Show database loading results
                db_loading = summary.get("database_loading", {})
                db_status = db_loading.get("status", "unknown")
                
                print(f"\n🗄️  Database Loading:")
                if db_status == "success":
                    print(f"  ✅ Successfully loaded {db_loading.get('endpoints_loaded', 0)} endpoints")
                    print(f"  📁 Combined file: {Path(db_loading.get('combined_filename', '')).name}")
                elif db_status == "error":
                    print(f"  ❌ Failed: {db_loading.get('error', 'Unknown error')}")
                elif db_status == "skipped":
                    print(f"  ⚠️  Skipped: {db_loading.get('reason', 'No reason given')}")
                elif db_status == "disabled":
                    print(f"  ⏸️  Disabled")
                elif db_status == "no_data":
                    print(f"  📭 No data to load")
                else:
                    print(f"  ❓ Status: {db_status}")
                
            else:
                print("❌ Grammar test failed")
            
            print("\n✨ Complete API discovery finished!")
        
        asyncio.run(main_with_args()) 