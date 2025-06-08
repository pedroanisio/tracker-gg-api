import asyncio
import json
import aiohttp
from urllib.parse import quote
from dotenv import load_dotenv
import os
import time

load_dotenv()

FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL")


def extract_json_from_html(html_content: str):
    """
    Extract JSON from HTML wrapper that flaresolverr returns.
    """
    try:
        import re
        # Look for JSON content between <pre> tags (common for API responses in browser)
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


async def call_api_endpoint(session, session_id, endpoint_url, endpoint_name, user_agent):
    """
    Call a specific API endpoint using the flaresolverr session.
    """
    print(f"\n📡 Testing: {endpoint_name}")
    print(f"🔗 URL: {endpoint_url}")
    
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
            
            print(f"📊 Status: {status}")
            
            if status == 200:
                print("✅ Success!")
                
                # Extract JSON from HTML wrapper
                json_data = extract_json_from_html(content)
                if json_data:
                    # Save the data
                    filename = f"{endpoint_name.replace('/', '_').replace('-', '_')}_data.json"
                    with open(filename, 'w') as f:
                        json.dump(json_data, f, indent=2)
                    
                    print(f"💾 Data saved to: {filename}")
                    
                    # Show preview of data structure
                    if isinstance(json_data, dict):
                        print(f"📄 Keys: {list(json_data.keys())}")
                        if 'data' in json_data and isinstance(json_data['data'], list):
                            print(f"📊 Data items: {len(json_data['data'])}")
                    elif isinstance(json_data, list):
                        print(f"📊 List items: {len(json_data)}")
                    
                    return {
                        "endpoint": endpoint_name,
                        "status": "success",
                        "data": json_data,
                        "filename": filename
                    }
                else:
                    print(f"⚠️  Could not extract JSON: {content[:100]}...")
                    return {
                        "endpoint": endpoint_name,
                        "status": "no_json",
                        "raw_content": content[:500]
                    }
            else:
                print(f"❌ Failed: {content[:100]}...")
                return {
                    "endpoint": endpoint_name,
                    "status": "failed",
                    "status_code": status,
                    "error": content[:200]
                }
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "endpoint": endpoint_name,
            "status": "error",
            "error": str(e)
        }


async def capture_all_api_endpoints(username: str):
    """
    Capture all API endpoints that the browser calls when loading tracker.gg.
    """
    
    session_id = f"complete_capture_{username.replace('#', '_')}_{int(time.time())}"
    encoded_username = quote(username)
    profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_username}"
    
    print("🕵️ Complete Tracker.gg API Capture")
    print("=" * 60)
    print(f"👤 Target: {username}")
    print(f"🔧 FlareSolverr: {FLARESOLVERR_URL}")
    print(f"🎯 Session: {session_id}")
    print()
    
    # Define all the API endpoints we want to test
    api_endpoints = [
        # Core data endpoints
        ("playlists", "https://api.tracker.gg/api/v1/valorant/db/playlists/"),
        ("seasons", "https://api.tracker.gg/api/v1/valorant/db/seasons/"),
        ("agents", "https://api.tracker.gg/api/v1/valorant/db/agents/"),
        ("maps", "https://api.tracker.gg/api/v1/valorant/db/maps/"),
        ("weapons", "https://api.tracker.gg/api/v1/valorant/db/weapons/"),
        
        # Wrapper and interaction endpoints
        ("interactions", "https://api.tracker.gg/api/v1/valorant/wrapper/interactions"),
        
        # Esports endpoints
        ("esports_tier_one", "https://api.tracker.gg/api/v1/valorant/esports/series/tier-one"),
        
        # Player-specific endpoints (the main one we want)
        ("premier_playlist", f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist?playlist=premier&source=web"),
        ("competitive_playlist", f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist?playlist=competitive&source=web"),
        ("unrated_playlist", f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist?playlist=unrated&source=web"),
        
        # Profile overview
        ("profile_overview", f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}"),
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Create session
            print("📋 Step 1: Creating FlareSolverr session...")
            create_payload = {
                "cmd": "sessions.create",
                "session": session_id
            }
            
            async with session.post(FLARESOLVERR_URL, json=create_payload) as response:
                result = await response.json()
                if result.get("status") != "ok":
                    print(f"❌ Failed to create session: {result}")
                    return None
                print("✅ Session created")
            
            # Step 2: Load the main profile page to establish proper cookies
            print("\n📋 Step 2: Loading profile page to establish session...")
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
                    print(f"❌ Failed to load profile page: {result}")
                    return None
                
                print("✅ Profile page loaded")
                print(f"🍪 Cookies: {len(solution.get('cookies', []))}")
                user_agent = solution.get("userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Step 3: Wait for page to fully load
            print("\n📋 Step 3: Waiting for page to fully load...")
            await asyncio.sleep(3)
            
            # Step 4: Call all API endpoints
            print("\n📋 Step 4: Calling all API endpoints...")
            print("=" * 40)
            
            for endpoint_name, endpoint_url in api_endpoints:
                result = await call_api_endpoint(session, session_id, endpoint_url, endpoint_name, user_agent)
                results.append(result)
                await asyncio.sleep(1)  # Small delay between requests
            
            # Step 5: Save summary
            print("\n📋 Step 5: Saving capture summary...")
            summary = {
                "username": username,
                "session_id": session_id,
                "timestamp": time.time(),
                "total_endpoints": len(api_endpoints),
                "successful_endpoints": len([r for r in results if r.get("status") == "success"]),
                "results": results
            }
            
            with open(f"complete_api_capture_{username.replace('#', '_')}.json", 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"💾 Summary saved")
            
            return summary
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
        
        finally:
            # Cleanup session
            try:
                print("\n📋 Step 6: Cleaning up session...")
                destroy_payload = {
                    "cmd": "sessions.destroy",
                    "session": session_id
                }
                async with session.post(FLARESOLVERR_URL, json=destroy_payload) as response:
                    result = await response.json()
                    if result.get("status") == "ok":
                        print("✅ Session cleaned up")
            except Exception as e:
                print(f"⚠️  Session cleanup error: {e}")


async def main():
    """Main function to run the complete API capture process."""
    
    username = "apolloZ#sun"
    
    # Run the complete capture
    summary = await capture_all_api_endpoints(username)
    
    if summary:
        print("\n🎉 CAPTURE COMPLETE!")
        print("=" * 60)
        print(f"📊 Total endpoints tested: {summary['total_endpoints']}")
        print(f"✅ Successful captures: {summary['successful_endpoints']}")
        print(f"❌ Failed captures: {summary['total_endpoints'] - summary['successful_endpoints']}")
        
        print(f"\n📄 Results summary:")
        for result in summary['results']:
            status_emoji = "✅" if result.get("status") == "success" else "❌"
            print(f"  {status_emoji} {result['endpoint']}: {result.get('status')}")
            
        print(f"\n💾 All data files saved to current directory")
        print(f"📋 Complete summary: complete_api_capture_{username.replace('#', '_')}.json")
        
        # Show which files were created
        print(f"\n📁 Created files:")
        for result in summary['results']:
            if result.get("status") == "success" and result.get("filename"):
                print(f"  📄 {result['filename']}")
    else:
        print("❌ Capture failed")
    
    print("\n✨ Process complete!")


if __name__ == "__main__":
    asyncio.run(main()) 