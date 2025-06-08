import asyncio
import json
from urllib.parse import quote
from flaresolverr_client import fetch_page_with_flaresolverr


async def test_premier_api_endpoint(username: str):
    """
    Test the tracker.gg API endpoint for Premier playlist data using flaresolverr.
    
    Args:
        username: The player's username (e.g., "player#1234")
    """
    print(f"Testing Premier API for username: {username}")
    
    # URL encode the username
    encoded_username = quote(username)
    
    # Construct the API URL
    api_url = f"https://tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist"
    params = "?playlist=premier&source=web"
    full_url = api_url + params
    
    print(f"Full API URL: {full_url}")
    
    try:
        print("Sending request through FlareSolverr...")
        response = await fetch_page_with_flaresolverr(full_url)
        
        if not response:
            print("❌ No response received from FlareSolverr")
            return None
        
        print(f"✅ Received response with content length: {len(response)} characters")
        
        # Try to parse as JSON
        try:
            json_data = json.loads(response)
            print("✅ Response is valid JSON")
            print("📄 JSON Response:")
            print(json.dumps(json_data, indent=2))
            return json_data
        except json.JSONDecodeError:
            print("⚠️  Response is not JSON, likely HTML content")
            print("📄 Raw Response (first 500 chars):")
            print(response[:500])
            print("..." if len(response) > 500 else "")
            return response
            
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        return None


async def test_working_profile_url(username: str):
    """
    Test the known working profile URL structure to see what we get.
    """
    encoded_username = quote(username)
    profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_username}"
    
    print(f"🧪 Testing working profile URL: {profile_url}")
    
    try:
        response = await fetch_page_with_flaresolverr(profile_url)
        
        if not response:
            print("❌ No response")
            return None
            
        print(f"✅ Received HTML response ({len(response)} chars)")
        
        # Look for any API calls or data in the HTML
        if "api/v2" in response:
            print("🔍 Found 'api/v2' references in HTML")
            # Extract lines containing api/v2
            lines = response.split('\n')
            api_lines = [line.strip() for line in lines if 'api/v2' in line]
            for line in api_lines[:5]:  # Show first 5 matches
                print(f"  📍 {line[:100]}...")
        
        if '"premier"' in response or 'premier' in response:
            print("🔍 Found 'premier' references in HTML")
            lines = response.split('\n')
            premier_lines = [line.strip() for line in lines if 'premier' in line.lower()]
            for line in premier_lines[:3]:  # Show first 3 matches
                print(f"  📍 {line[:100]}...")
                
        # Check for any JSON data embedded in script tags
        if 'window.__INITIAL_STATE__' in response or 'window.__DATA__' in response:
            print("🔍 Found embedded JSON data in HTML")
            
        return response
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


async def test_alternative_api_formats(username: str):
    """
    Test alternative API endpoint formats that might work.
    """
    encoded_username = quote(username)
    
    alternative_urls = [
        # Different API versions
        f"https://tracker.gg/api/v1/valorant/profile/riot/{encoded_username}",
        f"https://tracker.gg/api/valorant/profile/riot/{encoded_username}",
        
        # Internal API endpoints (guessing based on common patterns)
        f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}",
        f"https://public-api.tracker.gg/v2/valorant/standard/profile/riot/{encoded_username}",
        
        # Different segment structures
        f"https://tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}/overview",
        f"https://tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}/matches",
        
        # TRN API (tracker network)
        f"https://public-api.tracker.gg/v2/valorant/standard/profile/riot/{encoded_username}/segments/playlist?playlist=premier",
    ]
    
    print(f"🔬 Testing alternative API formats for: {username}")
    print("=" * 60)
    
    for i, url in enumerate(alternative_urls, 1):
        print(f"\n🧪 Alternative Test {i}/{len(alternative_urls)}:")
        print(f"   {url}")
        result = await test_single_endpoint(url)
        print("-" * 40)


async def test_multiple_endpoints(username: str):
    """
    Test multiple related API endpoints to see what's available.
    """
    encoded_username = quote(username)
    base_url = f"https://tracker.gg/api/v2/valorant/standard/profile/riot/{encoded_username}"
    
    endpoints_to_test = [
        f"{base_url}/segments/playlist?playlist=premier&source=web",
        f"{base_url}/segments/playlist?playlist=competitive&source=web", 
        f"{base_url}/segments/playlist?playlist=unrated&source=web",
        f"{base_url}/segments",
        f"{base_url}",
    ]
    
    print(f"Testing multiple endpoints for username: {username}")
    print("=" * 60)
    
    for i, url in enumerate(endpoints_to_test, 1):
        print(f"\n🧪 Test {i}/5: {url}")
        result = await test_single_endpoint(url)
        print("-" * 40)


async def test_single_endpoint(url: str):
    """Helper function to test a single endpoint."""
    try:
        response = await fetch_page_with_flaresolverr(url)
        
        if not response:
            print("❌ No response")
            return None
            
        # Check if it's JSON
        try:
            json_data = json.loads(response)
            print(f"✅ JSON response ({len(str(json_data))} chars)")
            if isinstance(json_data, dict):
                print(f"📊 Keys: {list(json_data.keys())}")
            return json_data
        except json.JSONDecodeError:
            print(f"⚠️  HTML/Text response ({len(response)} chars)")
            # Check if it's an error page
            if "404" in response or "Not Found" in response:
                print("🚫 Appears to be a 404 error")
            elif "403" in response or "Forbidden" in response:
                print("🚫 Appears to be a 403 forbidden")
            elif "<html" in response.lower():
                print("📄 HTML page returned")
                
                # Check for specific error indicators
                if "Page not found" in response or "404" in response:
                    print("   → Confirmed 404 error")
                elif "unauthorized" in response.lower() or "authentication" in response.lower():
                    print("   → May require authentication")
                    
            return response
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


async def main():
    """Main function to run the tests."""
    print("🚀 Testing Tracker.gg Premier API Endpoint")
    print("=" * 50)
    
    # Test with the specified username
    test_username = "apolloZ#sun"
    
    print(f"Using test username: {test_username}")
    print("Note: Change the username in the script if you want to test with a different player")
    print()
    
    # First test the working profile URL to understand the structure
    print("🏠 Testing working profile URL for reference:")
    await test_working_profile_url(test_username)
    
    print("\n" + "=" * 60)
    
    # Test the specific Premier endpoint
    print("🎯 Testing Premier-specific endpoint:")
    premier_result = await test_premier_api_endpoint(test_username)
    
    print("\n" + "=" * 60)
    
    # Test alternative API formats
    await test_alternative_api_formats(test_username)
    
    print("\n" + "=" * 60)
    
    # Test multiple related endpoints
    print("🔍 Testing original endpoints for comparison:")
    await test_multiple_endpoints(test_username)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 