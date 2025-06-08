import asyncio
import json
import aiohttp
from urllib.parse import quote
from dotenv import load_dotenv
import os
import time
from itertools import product

load_dotenv()

FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL")


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


async def call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent):
    """Call a specific API endpoint using the flaresolverr session."""
    print(f"\n📡 {endpoint_name}")
    print(f"🔗 {endpoint_url}")
    
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
                return {"endpoint": endpoint_name, "url": endpoint_url, "status": "failed", "status_code": status}
                
    except Exception as e:
        print(f"❌ Error: {e}")
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
    print()
    
    # Generate all endpoints
    endpoints = await generate_all_api_endpoints(username)
    print(f"🚀 Will test {len(endpoints)} endpoints")
    
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
            
            # Step 3: Wait for full page load
            print("\n📋 Step 3: Waiting for complete page load...")
            await asyncio.sleep(3)
            
            # Step 4: Test all endpoints systematically
            print("\n📋 Step 4: Testing all API endpoints...")
            print("=" * 50)
            
            successful = 0
            failed = 0
            
            for i, (endpoint_name, endpoint_url) in enumerate(endpoints):
                print(f"\n[{i+1}/{len(endpoints)}] Progress: {((i+1)/len(endpoints)*100):.1f}%")
                
                result = await call_api_with_session(session, session_id, endpoint_url, endpoint_name, user_agent)
                results.append(result)
                
                if result.get("status") == "success":
                    successful += 1
                else:
                    failed += 1
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.5)
                
                # Progress update every 10 requests
                if (i + 1) % 10 == 0:
                    print(f"\n📊 Progress Update: {successful} successful, {failed} failed")
            
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
            # Cleanup
            try:
                print("\n📋 Step 6: Cleaning up session...")
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
    
    # Run the complete grammar test
    summary = await test_complete_api_grammar(username)
    
    if summary:
        print("\n🎉 COMPLETE GRAMMAR TEST FINISHED!")
        print("=" * 60)
        print(f"📊 Total endpoints: {summary['total_endpoints']}")
        print(f"✅ Successful: {summary['successful_endpoints']}")
        print(f"❌ Failed: {summary['failed_endpoints']}")
        print(f"📈 Success rate: {summary['success_rate']}")
        
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
        
        print(f"\n📊 Breakdown:")
        print(f"  🔹 API v1 successful: {v1_success}")
        print(f"  🔹 API v2 successful: {v2_success}")
        
    else:
        print("❌ Grammar test failed")
    
    print("\n✨ Complete API discovery finished!")


if __name__ == "__main__":
    asyncio.run(main()) 