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
        # Look for JSON content between <pre> tags (common for API responses in browser)
        import re
        pre_pattern = r'<pre[^>]*>(.*?)</pre>'
        match = re.search(pre_pattern, html_content, re.DOTALL)
        
        if match:
            json_content = match.group(1).strip()
            try:
                return json.loads(json_content)
            except json.JSONDecodeError:
                # If that fails, try to find JSON directly in the content
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


async def capture_with_flaresolverr_session(username: str):
    """
    Use flaresolverr to create a persistent session and capture network requests.
    """
    
    session_id = f"valorant_session_{username.replace('#', '_')}_{int(time.time())}"
    encoded_username = quote(username)
    profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_username}"
    
    print(f"🔧 Using flaresolverr at: {FLARESOLVERR_URL}")
    print(f"👤 Target profile: {profile_url}")
    print(f"🎯 Session ID: {session_id}")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Create a new session
            print("\n📋 Step 1: Creating flaresolverr session...")
            create_payload = {
                "cmd": "sessions.create",
                "session": session_id
            }
            
            async with session.post(FLARESOLVERR_URL, json=create_payload) as response:
                result = await response.json()
                if result.get("status") == "ok":
                    print("✅ Session created successfully")
                else:
                    print(f"❌ Failed to create session: {result}")
                    return None
            
            # Step 2: Navigate to the page and let it fully load
            print("\n📋 Step 2: Loading profile page...")
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
                
                if result.get("status") == "ok":
                    print("✅ Page loaded successfully")
                    print(f"📊 Status: {solution.get('status')}")
                    print(f"🍪 Cookies captured: {len(solution.get('cookies', []))}")
                    print(f"📄 Response length: {len(solution.get('response', ''))} chars")
                    
                    # Extract cookies in the format needed for requests
                    cookies = solution.get("cookies", [])
                    cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
                    
                    print(f"\n🍪 Cookie summary:")
                    for cookie in cookies:
                        print(f"  📌 {cookie['name']}: {cookie['value'][:50]}...")
                    
                    # Now let's try to extract API calls from the network
                    # We'll wait a bit for the page to fully load and make its API calls
                    print("\n📋 Step 3: Waiting for page to fully load and make API calls...")
                    await asyncio.sleep(5)  # Give time for API calls to complete
                    
                    # Try to capture any additional network activity
                    # Some versions of flaresolverr might support this
                    network_payload = {
                        "cmd": "request.get",
                        "url": "https://api.tracker.gg/api/v1/valorant/db/playlists/",
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
                            "user-agent": solution.get("userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                        },
                        "maxTimeout": 30000
                    }
                    
                    print("\n📋 Step 4: Testing API call with session cookies...")
                    async with session.post(FLARESOLVERR_URL, json=network_payload) as api_response:
                        api_result = await api_response.json()
                        api_solution = api_result.get("solution", {})
                        
                        print(f"📡 API Status: {api_solution.get('status')}")
                        api_content = api_solution.get("response", "")
                        
                        if api_solution.get("status") == 200:
                            print("✅ API call successful!")
                            
                            # Extract JSON from HTML wrapper
                            json_data = extract_json_from_html(api_content)
                            if json_data:
                                print(f"📄 API Response: {json.dumps(json_data, indent=2)[:500]}...")
                                
                                # Save the API response
                                with open(f"api_playlists_{username.replace('#', '_')}.json", 'w') as f:
                                    json.dump(json_data, f, indent=2)
                                print(f"💾 API data saved")
                            else:
                                print(f"⚠️  Could not extract JSON from response: {api_content[:200]}...")
                        else:
                            print(f"❌ API call failed: {api_content[:200]}...")
                    
                    # Test the premier-specific endpoint
                    print("\n📋 Step 5: Testing Premier API endpoint...")
                    premier_payload = {
                        "cmd": "request.get",
                        "url": f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist?playlist=premier&source=web",
                        "session": session_id,
                        "headers": {
                            "accept": "application/json, text/plain, */*",
                            "accept-language": "en-US,en;q=0.9",
                            "cache-control": "no-cache",
                            "dnt": "1",
                            "origin": "https://tracker.gg",
                            "pragma": "no-cache",
                            "priority": "u=1, i",
                            "referer": profile_url,
                            "sec-ch-ua": '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                            "sec-ch-ua-mobile": "?0",
                            "sec-ch-ua-platform": '"Windows"',
                            "sec-fetch-dest": "empty",
                            "sec-fetch-mode": "cors",
                            "sec-fetch-site": "same-site",
                            "user-agent": solution.get("userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                        },
                        "maxTimeout": 30000
                    }
                    
                    async with session.post(FLARESOLVERR_URL, json=premier_payload) as premier_response:
                        premier_result = await premier_response.json()
                        premier_solution = premier_result.get("solution", {})
                        
                        print(f"🎯 Premier API Status: {premier_solution.get('status')}")
                        premier_content = premier_solution.get("response", "")
                        
                        if premier_solution.get("status") == 200:
                            print("✅ Premier API call successful!")
                            
                            # Extract JSON from HTML wrapper
                            premier_data = extract_json_from_html(premier_content)
                            if premier_data:
                                print(f"🏆 Premier data found!")
                                print(f"📄 Premier Response keys: {list(premier_data.keys()) if isinstance(premier_data, dict) else 'Not a dict'}")
                                
                                # Save the premier data
                                with open(f"premier_data_{username.replace('#', '_')}.json", 'w') as f:
                                    json.dump(premier_data, f, indent=2)
                                print(f"💾 Premier data saved to file")
                                
                                return {
                                    "status": "success",
                                    "cookies": cookies,
                                    "cookie_string": cookie_string,
                                    "premier_data": premier_data,
                                    "user_agent": solution.get("userAgent")
                                }
                            else:
                                print(f"⚠️  Could not extract JSON from Premier response: {premier_content[:200]}...")
                        else:
                            print(f"❌ Premier API call failed: {premier_content[:200]}...")
                    
                    return {
                        "status": "partial_success",
                        "cookies": cookies,
                        "cookie_string": cookie_string,
                        "html_content": solution.get("response", ""),
                        "user_agent": solution.get("userAgent")
                    }
                    
                else:
                    print(f"❌ Failed to load page: {result}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
        
        finally:
            # Cleanup: destroy the session
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
                    else:
                        print(f"⚠️  Session cleanup warning: {result}")
            except Exception as e:
                print(f"⚠️  Session cleanup error: {e}")


async def test_additional_endpoints(cookies, user_agent, username):
    """
    Test additional API endpoints using the captured cookies.
    """
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "cookie": cookies,
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
    }
    
    endpoints = [
        "https://api.tracker.gg/api/v1/valorant/db/seasons/",
        "https://api.tracker.gg/api/v1/valorant/db/agents/",
        "https://api.tracker.gg/api/v1/valorant/db/maps/",
        "https://api.tracker.gg/api/v1/valorant/db/weapons/",
        "https://api.tracker.gg/api/v1/valorant/wrapper/interactions"
    ]
    
    print(f"\n🧪 Testing additional endpoints with captured cookies...")
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                async with session.get(endpoint, headers=headers) as response:
                    content = await response.text()
                    endpoint_name = endpoint.split('/')[-2] + '_' + endpoint.split('/')[-1]
                    
                    print(f"📡 {endpoint_name}: Status {response.status}")
                    
                    if response.status == 200:
                        try:
                            data = json.loads(content)
                            filename = f"{endpoint_name}_{username.replace('#', '_')}.json"
                            with open(filename, 'w') as f:
                                json.dump(data, f, indent=2)
                            print(f"  ✅ Saved to {filename}")
                            results[endpoint_name] = data
                        except json.JSONDecodeError:
                            print(f"  ⚠️  Not JSON: {content[:100]}...")
                    else:
                        print(f"  ❌ Failed: {content[:100]}...")
                        
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    return results


async def main():
    """Main function to run the complete capture process."""
    
    username = "apolloZ#sun"
    
    print("🕵️ Advanced Tracker.gg Network Capture")
    print("=" * 60)
    print(f"Target: {username}")
    print()
    
    # Capture the session and try API calls
    result = await capture_with_flaresolverr_session(username)
    
    if result and result.get("status") in ["success", "partial_success"]:
        print(f"\n📊 Capture result: {result['status']}")
        
        if result.get("premier_data"):
            print("🎉 SUCCESS: Premier data captured!")
        else:
            print("⚠️  Premier data not captured, but session was successful")
            
            # Try additional endpoints with the captured cookies
            if result.get("cookie_string"):
                additional_results = await test_additional_endpoints(
                    result["cookie_string"], 
                    result["user_agent"], 
                    username
                )
                
                print(f"\n📈 Additional endpoints tested: {len(additional_results)}")
    else:
        print("❌ Failed to capture data")
    
    print("\n✨ Process complete!")


if __name__ == "__main__":
    asyncio.run(main()) 