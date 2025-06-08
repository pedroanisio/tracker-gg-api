import asyncio
import json
import aiohttp
from urllib.parse import quote
from dotenv import load_dotenv
import os

load_dotenv()

FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL")


async def capture_network_requests_with_flaresolverr(url: str, username: str):
    """
    Use flaresolverr to capture network requests during page load.
    """
    
    # Enhanced payload to capture network requests
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": 60000,
        "returnOnlyCookies": False,
        "returnRawHtml": True,
        # Request to return cookies and other info
        "session": f"session_{username.replace('#', '_')}",
    }

    print(f"🌐 Capturing network requests for: {url}")
    print(f"🔧 Using flaresolverr at: {FLARESOLVERR_URL}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(FLARESOLVERR_URL, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                
                solution = result.get("solution", {})
                
                # Extract all available data
                data = {
                    "url": url,
                    "status": solution.get("status"),
                    "cookies": solution.get("cookies", []),
                    "userAgent": solution.get("userAgent", ""),
                    "headers": solution.get("headers", {}),
                    "response": solution.get("response", ""),
                }
                
                print(f"✅ Page loaded successfully")
                print(f"📊 Status: {data['status']}")
                print(f"🍪 Cookies captured: {len(data['cookies'])}")
                print(f"📄 Response length: {len(data['response'])} chars")
                
                return data
                
        except aiohttp.ClientResponseError as e:
            print(f"❌ HTTP error occurred: {e.status} - {e.message}")
            return None
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            return None


async def extract_network_calls_from_page(url: str, username: str):
    """
    Load the page and try to extract network call information.
    """
    
    # First, get the page data
    page_data = await capture_network_requests_with_flaresolverr(url, username)
    
    if not page_data:
        print("❌ Failed to load page")
        return None
    
    # Save the captured data
    filename = f"captured_data_{username.replace('#', '_')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(page_data, f, indent=2, default=str)
    
    print(f"💾 Captured data saved to: {filename}")
    
    # Analyze the HTML for embedded network calls or API patterns
    html_content = page_data.get("response", "")
    cookies = page_data.get("cookies", [])
    
    print("\n🔍 Analyzing captured data...")
    
    # Look for API endpoints in the HTML
    import re
    api_patterns = [
        r'https://api\.tracker\.gg/api/v[0-9]+/[^"\s]+',
        r'https://api\.tracker\.gg/[^"\s]+',
        r'/api/v[0-9]+/[^"\s]+',
    ]
    
    found_apis = set()
    for pattern in api_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        found_apis.update(matches)
    
    if found_apis:
        print(f"🎯 Found {len(found_apis)} API endpoints in HTML:")
        for api in sorted(found_apis):
            print(f"  📡 {api}")
    
    # Extract cookies for API calls
    cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
    
    print(f"\n🍪 Cookie string for API calls:")
    print(f"   {cookie_string[:100]}...")
    
    # Generate test API calls with proper headers
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "cookie": cookie_string,
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
        "user-agent": page_data.get("userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    }
    
    return {
        "page_data": page_data,
        "found_apis": list(found_apis),
        "headers": headers,
        "cookies": cookies
    }


async def test_api_endpoints_with_captured_data(username: str, captured_data):
    """
    Test the discovered API endpoints with the captured cookies and headers.
    """
    
    headers = captured_data["headers"]
    
    # Test the main API endpoints we expect
    test_endpoints = [
        "https://api.tracker.gg/api/v1/valorant/db/playlists/",
        "https://api.tracker.gg/api/v1/valorant/wrapper/interactions",
        "https://api.tracker.gg/api/v1/valorant/db/seasons/",
        "https://api.tracker.gg/api/v1/valorant/db/agents/",
        f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{quote(username)}/segments/playlist?playlist=premier&source=web",
    ]
    
    # Add any endpoints found in the HTML
    test_endpoints.extend(captured_data["found_apis"])
    
    print(f"\n🧪 Testing {len(test_endpoints)} API endpoints...")
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, endpoint in enumerate(test_endpoints, 1):
            print(f"\n📡 Test {i}/{len(test_endpoints)}: {endpoint}")
            
            try:
                async with session.get(endpoint, headers=headers, timeout=10) as response:
                    content = await response.text()
                    
                    result = {
                        "endpoint": endpoint,
                        "status": response.status,
                        "content_length": len(content),
                        "content_type": response.headers.get("content-type", ""),
                        "success": response.status == 200,
                    }
                    
                    if response.status == 200:
                        print(f"✅ Success! ({len(content)} chars)")
                        
                        # Try to parse as JSON
                        try:
                            json_data = json.loads(content)
                            result["is_json"] = True
                            result["json_keys"] = list(json_data.keys()) if isinstance(json_data, dict) else None
                            print(f"📄 JSON response with keys: {result['json_keys']}")
                            
                            # Save successful responses
                            if 'premier' in endpoint.lower() or 'playlist' in endpoint.lower():
                                filename = f"premier_data_{username.replace('#', '_')}.json"
                                with open(filename, 'w') as f:
                                    json.dump(json_data, f, indent=2)
                                print(f"💾 Premier data saved to: {filename}")
                        except json.JSONDecodeError:
                            result["is_json"] = False
                            print(f"📄 Non-JSON response")
                    else:
                        print(f"❌ Error: {response.status}")
                        if len(content) < 500:
                            print(f"   Response: {content}")
                    
                    results.append(result)
                    
            except Exception as e:
                print(f"❌ Request failed: {e}")
                results.append({
                    "endpoint": endpoint,
                    "status": None,
                    "error": str(e),
                    "success": False
                })
    
    return results


async def main():
    """Main function to capture network requests and test API endpoints."""
    
    username = "apolloZ#sun"
    profile_url = f"https://tracker.gg/valorant/profile/riot/{quote(username)}"
    
    print("🕵️ Network Request Capture Tool")
    print("=" * 50)
    print(f"Target: {username}")
    print(f"URL: {profile_url}")
    print()
    
    # Step 1: Capture page data and network information
    print("📡 Step 1: Capturing page data...")
    captured_data = await extract_network_calls_from_page(profile_url, username)
    
    if not captured_data:
        print("❌ Failed to capture page data")
        return
    
    # Step 2: Test discovered API endpoints
    print("\n🧪 Step 2: Testing API endpoints...")
    api_results = await test_api_endpoints_with_captured_data(username, captured_data)
    
    # Step 3: Summary
    print("\n📊 Summary:")
    successful_apis = [r for r in api_results if r.get("success")]
    print(f"✅ Successful API calls: {len(successful_apis)}")
    
    for result in successful_apis:
        print(f"  📡 {result['endpoint']}")
        if result.get("json_keys"):
            print(f"      Keys: {result['json_keys']}")
    
    # Save final results
    final_results = {
        "username": username,
        "captured_data": captured_data,
        "api_test_results": api_results,
        "successful_endpoints": successful_apis
    }
    
    results_filename = f"network_analysis_{username.replace('#', '_')}.json"
    with open(results_filename, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n💾 Complete analysis saved to: {results_filename}")


if __name__ == "__main__":
    asyncio.run(main()) 