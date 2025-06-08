import asyncio
from urllib.parse import quote
from flaresolverr_client import fetch_page_with_flaresolverr


async def extract_raw_json_line(username: str):
    """
    Extract the raw line containing window.__INITIAL_STATE__ and save it to a file.
    """
    encoded_username = quote(username)
    profile_url = f"https://tracker.gg/valorant/profile/riot/{encoded_username}"
    
    print(f"📍 Fetching: {profile_url}")
    
    html_content = await fetch_page_with_flaresolverr(profile_url)
    
    if not html_content:
        print("❌ No HTML content received")
        return
    
    lines = html_content.split('\n')
    
    for i, line in enumerate(lines):
        if 'window.__INITIAL_STATE__' in line:
            print(f"📍 Found window.__INITIAL_STATE__ at line {i+1}")
            
            # Save the raw line to a file
            filename = f"raw_json_line_{username.replace('#', '_')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(line)
            
            print(f"💾 Raw line saved to: {filename}")
            print(f"📏 Line length: {len(line)} characters")
            
            # Try to find where the JSON starts and potentially ends
            start_pos = line.find('{')
            if start_pos != -1:
                json_part = line[start_pos:]
                
                # Look for potential JSON end markers
                potential_ends = []
                
                # Look for }; followed by something else
                import re
                for match in re.finditer(r'};', json_part):
                    potential_ends.append(match.end())
                
                print(f"🔍 JSON starts at position: {start_pos}")
                print(f"🔍 Found {len(potential_ends)} potential end positions: {potential_ends[:5]}")
                
                # Try extracting JSON with different end positions
                for i, end_pos in enumerate(potential_ends[:3]):
                    try:
                        candidate_json = json_part[:end_pos-1]  # Exclude the semicolon
                        
                        # Save each candidate to a separate file
                        candidate_filename = f"json_candidate_{i+1}_{username.replace('#', '_')}.json"
                        with open(candidate_filename, 'w', encoding='utf-8') as f:
                            f.write(candidate_json)
                        
                        print(f"💾 JSON candidate {i+1} saved to: {candidate_filename} ({len(candidate_json)} chars)")
                        
                        # Try to parse it
                        import json
                        try:
                            parsed = json.loads(candidate_json)
                            print(f"✅ JSON candidate {i+1} is valid! Top-level keys: {list(parsed.keys())}")
                            
                            # Look for premier-related data
                            def find_premier_references(obj, path=""):
                                refs = []
                                if isinstance(obj, dict):
                                    for key, value in obj.items():
                                        current_path = f"{path}.{key}" if path else key
                                        if any(term in key.lower() for term in ['premier', 'playlist', 'segment']):
                                            refs.append(current_path)
                                        if isinstance(value, (dict, list)):
                                            refs.extend(find_premier_references(value, current_path))
                                elif isinstance(obj, list):
                                    for i, item in enumerate(obj):
                                        refs.extend(find_premier_references(item, f"{path}[{i}]"))
                                return refs
                            
                            premier_refs = find_premier_references(parsed)
                            if premier_refs:
                                print(f"🎯 Found premier references: {premier_refs}")
                            else:
                                print("❌ No premier references found in this candidate")
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON candidate {i+1} is invalid: {e}")
                            
                    except Exception as e:
                        print(f"❌ Error processing candidate {i+1}: {e}")
            
            break
    else:
        print("❌ No line with window.__INITIAL_STATE__ found")


async def main():
    username = "apolloZ#sun"
    print(f"🔬 Extracting raw JSON for: {username}")
    await extract_raw_json_line(username)


if __name__ == "__main__":
    asyncio.run(main()) 