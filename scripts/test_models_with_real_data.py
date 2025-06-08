"""
Test script to validate Pydantic models against real captured data.
"""

import json
import sys
from pathlib import Path
from models.tracker_models import (
    V1AggregatedResponse, V2PlaylistResponse, V2LoadoutResponse,
    PlaylistSegment, LoadoutSegment, AggregatedData,
    Playlist, SegmentType, LoadoutType
)


def test_v1_aggregated_data():
    """Test v1 aggregated data models against real data."""
    print("🧪 Testing v1 aggregated data...")
    
    try:
        # Test with premier aggregated data
        with open("data/grammar_v1_aggregated_premier_current_0.json", "r") as f:
            data = json.load(f)
        
        response = V1AggregatedResponse(**data)
        print(f"✅ V1 Premier aggregated: found={response.data.found}, parties={len(response.data.parties)}")
        
        # Test with competitive aggregated data (has heatmap)
        with open("data/grammar_v1_aggregated_competitive_current_0.json", "r") as f:
            data = json.load(f)
        
        response = V1AggregatedResponse(**data)
        print(f"✅ V1 Competitive aggregated: found={response.data.found}, heatmap_entries={len(response.data.heatmap)}")
        
        if response.data.heatmap:
            first_entry = response.data.heatmap[0]
            print(f"   📊 First heatmap entry: {first_entry.date.date()}, kills={first_entry.values.kills}")
        
        return True
    except Exception as e:
        print(f"❌ V1 aggregated test failed: {e}")
        return False


def test_v2_playlist_data():
    """Test v2 playlist segment models against real data."""
    print("\n🧪 Testing v2 playlist data...")
    
    try:
        # Test with premier playlist data
        with open("data/grammar_v2_segment_playlist_premier_web.json", "r") as f:
            data = json.load(f)
        
        response = V2PlaylistResponse(**data)
        print(f"✅ V2 Premier playlist: {len(response.data)} segments")
        
        if response.data:
            segment = response.data[0]
            print(f"   📋 Segment type: {segment.type}")
            print(f"   🎮 Playlist: {segment.attributes.playlist}")
            print(f"   📊 Matches played: {segment.stats.matchesPlayed.value}")
            print(f"   🏆 Win rate: {segment.stats.matchesWinPct.displayValue}")
            print(f"   ⚔️ K/D ratio: {segment.stats.kDRatio.displayValue}")
            print(f"   🎯 ACS: {segment.stats.scorePerRound.displayValue}")
        
        return True
    except Exception as e:
        print(f"❌ V2 playlist test failed: {e}")
        return False


def test_v2_loadout_data():
    """Test v2 loadout segment models against real data."""
    print("\n🧪 Testing v2 loadout data...")
    
    try:
        # Test with premier loadout data
        with open("data/grammar_v2_segment_loadout_premier_current.json", "r") as f:
            data = json.load(f)
        
        response = V2LoadoutResponse(**data)
        print(f"✅ V2 Premier loadout: {len(response.data)} segments")
        
        if response.data:
            segment = response.data[0]
            print(f"   📋 Loadout type: {segment.attributes.key}")
            print(f"   🔫 Weapon: {segment.metadata.name}")
            print(f"   ⚔️ Kills: {segment.stats.kills.value}")
            print(f"   💀 Deaths: {segment.stats.deaths.value}")
            print(f"   📊 K/D: {segment.stats.kDRatio.displayValue}")
            print(f"   🎯 Headshot %: {segment.stats.headshotsPercentage.displayValue}")
        
        return True
    except Exception as e:
        print(f"❌ V2 loadout test failed: {e}")
        return False


def test_model_properties():
    """Test model properties and methods."""
    print("\n🧪 Testing model properties...")
    
    try:
        # Test enums
        assert Playlist.PREMIER == "premier"
        assert SegmentType.LOADOUT == "loadout"
        assert LoadoutType.PISTOL == "pistol"
        print("✅ Enums working correctly")
        
        # Test that all playlist enum values are strings
        for playlist in Playlist:
            assert isinstance(playlist.value, str)
        print("✅ All playlist values are valid strings")
        
        return True
    except Exception as e:
        print(f"❌ Model properties test failed: {e}")
        return False


def validate_data_coverage():
    """Validate that we have coverage for all major data types."""
    print("\n🧪 Validating data coverage...")
    
    data_dir = Path("data")
    json_files = list(data_dir.glob("*.json"))
    
    print(f"📊 Total JSON files captured: {len(json_files)}")
    
    # Count different types
    v1_files = [f for f in json_files if "v1_aggregated" in f.name]
    v2_playlist_files = [f for f in json_files if "v2_segment_playlist" in f.name]
    v2_loadout_files = [f for f in json_files if "v2_segment_loadout" in f.name]
    
    print(f"📈 V1 aggregated files: {len(v1_files)}")
    print(f"📈 V2 playlist files: {len(v2_playlist_files)}")
    print(f"📈 V2 loadout files: {len(v2_loadout_files)}")
    
    # Check for premier-specific files
    premier_files = [f for f in json_files if "premier" in f.name]
    print(f"🏆 Premier-related files: {len(premier_files)}")
    
    # Check for competitive files
    competitive_files = [f for f in json_files if "competitive" in f.name]
    print(f"🎯 Competitive-related files: {len(competitive_files)}")
    
    return True


def main():
    """Run all tests."""
    print("🔬 Testing Pydantic Models Against Real Data")
    print("=" * 60)
    
    tests = [
        test_v1_aggregated_data,
        test_v2_playlist_data,
        test_v2_loadout_data,
        test_model_properties,
        validate_data_coverage
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Models are ready for production use.")
        return True
    else:
        print("⚠️  Some tests failed. Review the models.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 