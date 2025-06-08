"""
Unified Data Loader for Tracker.gg API Data.
Combines legacy and improved functionality with deduplication and error handling.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlmodel import Session, select
import re

from ..shared.database import (
    engine, get_or_create_player, create_segment_with_stats, 
    log_ingestion_operation, Player, PlayerSegment, StatisticValue,
    HeatmapData, PartyStatistic, init_db
)
from ..shared.utils import setup_logger

logger = setup_logger(__name__)

class UnifiedTrackerDataLoader:
    """Unified data loader for all tracker.gg data formats"""
    
    def __init__(self, data_directory: str = "./data"):
        self.data_directory = Path(data_directory)
        self.stats = {
            "files_processed": 0,
            "files_successful": 0,
            "files_failed": 0,
            "players_created": 0,
            "segments_created": 0,
            "stats_created": 0,
            "heatmap_entries": 0,
            "party_entries": 0
        }
    
    def load_all_files(self) -> Dict[str, Any]:
        """Load all JSON files from the data directory"""
        init_db()
        
        json_files = list(self.data_directory.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {self.data_directory}")
            return self.stats
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        with Session(engine) as session:
            for json_file in json_files:
                try:
                    self.load_file(session, json_file)
                    self.stats["files_successful"] += 1
                    logger.info(f"✓ Loaded {json_file.name}")
                except Exception as e:
                    self.stats["files_failed"] += 1
                    logger.error(f"✗ Failed to load {json_file.name}: {e}")
                    
                    log_ingestion_operation(
                        session=session,
                        operation_type="file_load",
                        source=str(json_file),
                        status="error",
                        details=str(e)
                    )
                
                self.stats["files_processed"] += 1
            
            session.commit()
        
        logger.info(f"Loading complete. Processed {self.stats['files_processed']} files")
        logger.info(f"Success: {self.stats['files_successful']}, Failed: {self.stats['files_failed']}")
        
        return self.stats
    
    def load_file(self, session: Session, file_path: Path) -> None:
        """Load a single JSON file with automatic format detection"""
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract riot_id
        riot_id = self._extract_riot_id(data, file_path)
        
        # Get or create player
        player = get_or_create_player(session, riot_id)
        if not hasattr(player, '_was_existing'):
            self.stats["players_created"] += 1
        
        # Auto-detect format and process
        if "capture_method" in data and data["capture_method"] == "browser_interception":
            self._load_browser_intercepted_data(session, player.id, data, file_path)
        elif "endpoints" in data:
            self._load_endpoints_format(session, player.id, data, file_path)
        elif "data" in data and "original_filename" in data:
            self._load_direct_api_response(session, player.id, data, file_path)
        else:
            logger.warning(f"Unknown data format in {file_path}")
            return
        
        # Log successful ingestion
        log_ingestion_operation(
            session=session,
            operation_type="file_load",
            source=str(file_path),
            player_riot_id=riot_id,
            status="success",
            records_processed=len(data.get("endpoints", {})),
            records_inserted=self.stats["segments_created"],
            details=f"Loaded {data.get('capture_method', 'auto-detected')} format data"
        )
    
    def _extract_riot_id(self, data: Dict[str, Any], file_path: Path) -> str:
        """Extract riot_id from data or filename"""
        riot_id = data.get("riot_id")
        
        if not riot_id:
            filename = file_path.stem
            if filename.startswith(("capture_", "browser_capture_", "enhanced_update_")):
                parts = filename.split("_")
                if len(parts) >= 3:
                    # Handle different filename patterns
                    if "enhanced_update" in filename:
                        riot_id = f"{parts[-3]}#{parts[-2]}"
                    else:
                        riot_id = f"{parts[1]}#{parts[2]}"
        
        if not riot_id:
            raise ValueError(f"Could not determine riot_id from file {file_path}")
        
        return riot_id
    
    def _load_browser_intercepted_data(self, session: Session, player_id: int, 
                                     data: Dict[str, Any], source_file: Path) -> None:
        """Load browser-intercepted format data"""
        
        endpoints = data.get("endpoints", {})
        
        for endpoint_name, endpoint_data in endpoints.items():
            if endpoint_data.get("status") != "success":
                continue
            
            api_data = endpoint_data.get("data", {})
            endpoint_type = endpoint_data.get("endpoint_type", "")
            playlist = endpoint_data.get("playlist", "")
            
            try:
                if endpoint_type == "v1_aggregated":
                    self._load_v1_aggregated_data(
                        session, player_id, endpoint_name, 
                        {"data": api_data}, source_file, playlist
                    )
                elif endpoint_type == "v2_playlist":
                    self._load_v2_playlist_data(
                        session, player_id, endpoint_name, 
                        api_data, source_file, playlist
                    )
                elif endpoint_type == "v2_loadout":
                    self._load_v2_loadout_data(
                        session, player_id, endpoint_name, 
                        api_data, source_file
                    )
                    
            except Exception as e:
                logger.error(f"Failed to process endpoint {endpoint_name}: {e}")
                continue
    
    def _load_endpoints_format(self, session: Session, player_id: int,
                              data: Dict[str, Any], source_file: Path) -> None:
        """Load legacy endpoints format"""
        
        endpoints = data.get("endpoints", {})
        
        for endpoint_name, endpoint_data in endpoints.items():
            if endpoint_data.get("status") != "success":
                continue
                
            api_data = endpoint_data.get("data", {})
            
            try:
                if endpoint_name.startswith("v1_") and "aggregated" in endpoint_name:
                    self._load_v1_aggregated_data(
                        session, player_id, endpoint_name, 
                        api_data, source_file
                    )
                elif endpoint_name.startswith("v2_") and "playlist" in endpoint_name:
                    self._load_v2_playlist_data(
                        session, player_id, endpoint_name, 
                        api_data, source_file
                    )
                elif endpoint_name.startswith("v2_") and "loadout" in endpoint_name:
                    self._load_v2_loadout_data(
                        session, player_id, endpoint_name, 
                        api_data, source_file
                    )
                    
            except Exception as e:
                logger.error(f"Failed to process endpoint {endpoint_name}: {e}")
                continue
    
    def _load_direct_api_response(self, session: Session, player_id: int,
                                data: Dict[str, Any], source_file: Path) -> None:
        """Load direct API response format"""
        
        original_filename = data.get("original_filename", "")
        api_data = data.get("data", {})
        
        if not isinstance(api_data, dict) or not api_data.get("found", False):
            return
        
        # Determine endpoint type from filename
        if "v1_aggregated" in original_filename:
            parts = original_filename.split("_")
            if len(parts) >= 3:
                playlist = parts[2]
                endpoint_name = f"v1_{playlist}_aggregated"
                self._load_v1_aggregated_data(
                    session, player_id, endpoint_name, 
                    {"data": api_data}, source_file, playlist
                )
        
        elif "v2_playlist" in original_filename:
            parts = original_filename.split("_")
            if len(parts) >= 3:
                playlist = parts[2]
                endpoint_name = f"v2_{playlist}_playlist"
                self._load_v2_playlist_data(
                    session, player_id, endpoint_name, 
                    api_data, source_file, playlist
                )
        
        elif "v2_loadout" in original_filename:
            endpoint_name = "v2_loadout"
            self._load_v2_loadout_data(
                session, player_id, endpoint_name, 
                api_data, source_file
            )
    
    def _load_v1_aggregated_data(self, session: Session, player_id: int,
                               endpoint_name: str, api_data: Dict[str, Any],
                               source_file: Path, playlist: str = None) -> None:
        """Load V1 aggregated data with deduplication"""
        
        if not playlist:
            playlist = endpoint_name.replace("v1_", "").replace("_aggregated", "")
        
        data_section = api_data.get("data", {})
        
        # Load heatmap data with deduplication
        heatmap_data = data_section.get("heatmap", [])
        for entry in heatmap_data:
            try:
                date_str = entry["date"]
                if date_str.endswith("Z"):
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    date_obj = datetime.fromisoformat(date_str)
                
                # Check for existing entry
                existing_entry = session.exec(
                    select(HeatmapData).where(
                        HeatmapData.player_id == player_id,
                        HeatmapData.playlist == playlist,
                        HeatmapData.date == date_obj
                    )
                ).first()
                
                if existing_entry:
                    # Update existing
                    for key, value in entry["values"].items():
                        snake_key = self._camel_to_snake(key)
                        if hasattr(existing_entry, snake_key):
                            setattr(existing_entry, snake_key, value)
                    session.add(existing_entry)
                else:
                    # Create new
                    heatmap_entry = HeatmapData(
                        player_id=player_id,
                        playlist=playlist,
                        date=date_obj,
                        playtime=entry["values"].get("playtime", 0),
                        kd_ratio=entry["values"].get("kd", 0.0),
                        placement=entry["values"].get("placement", 0.0),
                        score=entry["values"].get("score", 0.0),
                        kills=entry["values"].get("kills", 0),
                        deaths=entry["values"].get("deaths", 0),
                        hs_accuracy=entry["values"].get("hsAccuracy", 0.0),
                        matches=entry["values"].get("matches", 0),
                        wins=entry["values"].get("wins", 0),
                        losses=entry["values"].get("losses", 0),
                        win_pct=entry["values"].get("winPct", 0.0),
                        adr=entry["values"].get("adr", 0.0)
                    )
                    session.add(heatmap_entry)
                    self.stats["heatmap_entries"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process heatmap entry: {e}")
                continue
        
        # Load party data with deduplication
        parties_data = data_section.get("parties", [])
        for party in parties_data:
            try:
                existing_party = session.exec(
                    select(PartyStatistic).where(
                        PartyStatistic.player_id == player_id,
                        PartyStatistic.playlist == playlist,
                        PartyStatistic.party_number == party["party"]
                    )
                ).first()
                
                if existing_party:
                    # Update existing
                    for key, value in party["data"].items():
                        snake_key = self._camel_to_snake(key)
                        if hasattr(existing_party, snake_key):
                            setattr(existing_party, snake_key, value)
                    session.add(existing_party)
                else:
                    # Create new
                    party_stat = PartyStatistic(
                        player_id=player_id,
                        playlist=playlist,
                        party_number=party["party"],
                        kd_ratio=party["data"].get("kd", 0.0),
                        placement=party["data"].get("placement", 0.0),
                        matches=party["data"].get("matches", 0),
                        wins=party["data"].get("wins", 0),
                        losses=party["data"].get("losses", 0),
                        win_pct=party["data"].get("winPct", 0.0)
                    )
                    session.add(party_stat)
                    self.stats["party_entries"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process party entry: {e}")
                continue
    
    def _load_v2_playlist_data(self, session: Session, player_id: int,
                             endpoint_name: str, api_data: Dict[str, Any],
                             source_file: Path, playlist: str = None) -> None:
        """Load V2 playlist data with deduplication"""
        
        if not playlist:
            playlist = endpoint_name.replace("v2_", "").replace("_playlist", "")
        
        segments = api_data.get("data", [])
        
        for segment_data in segments:
            try:
                segment_key = segment_data["attributes"]["key"]
                
                # Check for existing segment
                existing_segment = session.exec(
                    select(PlayerSegment).where(
                        PlayerSegment.player_id == player_id,
                        PlayerSegment.segment_type == "playlist",
                        PlayerSegment.segment_key == segment_key,
                        PlayerSegment.playlist == playlist
                    )
                ).first()
                
                if existing_segment:
                    # Update existing
                    existing_segment.captured_at = datetime.utcnow()
                    if segment_data.get("expiryDate"):
                        existing_segment.expiry_date = datetime.fromisoformat(
                            segment_data["expiryDate"].replace("Z", "+00:00")
                        )
                    session.add(existing_segment)
                    self._update_segment_stats(session, existing_segment.id, segment_data["stats"])
                else:
                    # Create new
                    segment = create_segment_with_stats(
                        session=session,
                        player_id=player_id,
                        segment_type="playlist",
                        segment_key=segment_key,
                        stats_data=segment_data["stats"],
                        metadata=segment_data["metadata"],
                        playlist=playlist,
                        season_id=segment_data["attributes"].get("seasonId"),
                        schema_version=segment_data["metadata"]["schema"],
                        display_name=segment_data["metadata"]["name"],
                        expiry_date=datetime.fromisoformat(
                            segment_data["expiryDate"].replace("Z", "+00:00")
                        ),
                        source_url=endpoint_name,
                        source_file=str(source_file)
                    )
                    
                    self.stats["segments_created"] += 1
                    self.stats["stats_created"] += len(segment_data["stats"])
                    
            except Exception as e:
                logger.error(f"Failed to process playlist segment: {e}")
                continue
    
    def _load_v2_loadout_data(self, session: Session, player_id: int,
                            endpoint_name: str, api_data: Dict[str, Any],
                            source_file: Path) -> None:
        """Load V2 loadout data with deduplication"""
        
        segments = api_data.get("data", [])
        
        for segment_data in segments:
            try:
                segment_key = segment_data["attributes"]["key"]
                
                # Check for existing loadout segment
                existing_segment = session.exec(
                    select(PlayerSegment).where(
                        PlayerSegment.player_id == player_id,
                        PlayerSegment.segment_type == "loadout",
                        PlayerSegment.segment_key == segment_key
                    )
                ).first()
                
                if existing_segment:
                    # Update existing
                    existing_segment.captured_at = datetime.utcnow()
                    if segment_data.get("expiryDate"):
                        existing_segment.expiry_date = datetime.fromisoformat(
                            segment_data["expiryDate"].replace("Z", "+00:00")
                        )
                    session.add(existing_segment)
                    self._update_segment_stats(session, existing_segment.id, segment_data["stats"])
                else:
                    # Create new
                    segment = create_segment_with_stats(
                        session=session,
                        player_id=player_id,
                        segment_type="loadout",
                        segment_key=segment_key,
                        stats_data=segment_data["stats"],
                        metadata=segment_data["metadata"],
                        playlist=segment_data["attributes"].get("playlist"),
                        season_id=segment_data["attributes"].get("seasonId"),
                        schema_version=segment_data["metadata"]["schema"],
                        display_name=segment_data["metadata"]["name"],
                        expiry_date=datetime.fromisoformat(
                            segment_data["expiryDate"].replace("Z", "+00:00")
                        ),
                        source_url=endpoint_name,
                        source_file=str(source_file)
                    )
                    
                    self.stats["segments_created"] += 1
                    self.stats["stats_created"] += len(segment_data["stats"])
                    
            except Exception as e:
                logger.error(f"Failed to process loadout segment: {e}")
                continue
    
    def _update_segment_stats(self, session: Session, segment_id: int, 
                            stats_data: Dict[str, Any]) -> None:
        """Update statistics for an existing segment"""
        
        for stat_name, stat_data in stats_data.items():
            if not isinstance(stat_data, dict) or 'value' not in stat_data:
                continue
            
            # Find existing stat
            existing_stat = session.exec(
                select(StatisticValue).where(
                    StatisticValue.segment_id == segment_id,
                    StatisticValue.stat_name == stat_name
                )
            ).first()
            
            if existing_stat:
                # Update existing stat
                existing_stat.value = float(stat_data['value'])
                existing_stat.display_value = stat_data.get('displayValue', str(stat_data['value']))
                existing_stat.display_name = stat_data.get('displayName', stat_name)
                existing_stat.display_category = stat_data.get('displayCategory', '')
                existing_stat.category = stat_data.get('category', '')
                existing_stat.display_type = stat_data.get('displayType', 'Number')
                existing_stat.description = stat_data.get('description')
                existing_stat.stat_metadata = stat_data.get('metadata', {})
                session.add(existing_stat)
            else:
                # Create new stat
                stat_value = StatisticValue(
                    segment_id=segment_id,
                    stat_name=stat_name,
                    display_name=stat_data.get('displayName', stat_name),
                    display_category=stat_data.get('displayCategory', ''),
                    category=stat_data.get('category', ''),
                    value=float(stat_data['value']),
                    display_value=stat_data.get('displayValue', str(stat_data['value'])),
                    display_type=stat_data.get('displayType', 'Number'),
                    description=stat_data.get('description'),
                    stat_metadata=stat_data.get('metadata', {})
                )
                session.add(stat_value)
                self.stats["stats_created"] += 1
    
    def _camel_to_snake(self, camel_case: str) -> str:
        """Convert camelCase to snake_case"""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_case).lower()
    
    def get_loading_stats(self) -> Dict[str, Any]:
        """Get current loading statistics"""
        return self.stats.copy()


# Convenience functions
def load_data_from_directory(data_dir: str = "./data") -> Dict[str, Any]:
    """Load all data from a directory"""
    loader = UnifiedTrackerDataLoader(data_dir)
    return loader.load_all_files()


def load_single_file(file_path: str) -> Dict[str, Any]:
    """Load a single JSON file"""
    init_db()
    
    loader = UnifiedTrackerDataLoader()
    
    with Session(engine) as session:
        try:
            loader.load_file(session, Path(file_path))
            session.commit()
            loader.stats["files_successful"] = 1
            loader.stats["files_processed"] = 1
            logger.info(f"Successfully loaded {file_path}")
        except Exception as e:
            loader.stats["files_failed"] = 1
            loader.stats["files_processed"] = 1
            logger.error(f"Failed to load {file_path}: {e}")
            
            log_ingestion_operation(
                session=session,
                operation_type="file_load",
                source=file_path,
                status="error",
                details=str(e)
            )
            session.commit()
    
    return loader.get_loading_stats()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Tracker.gg data loader")
    parser.add_argument("--data-dir", default="./data", help="Directory containing JSON files")
    parser.add_argument("--file", help="Load a single file")
    parser.add_argument("--init-db", action="store_true", help="Initialize database only")
    
    args = parser.parse_args()
    
    if args.init_db:
        init_db()
        print("Database initialized successfully!")
    elif args.file:
        stats = load_single_file(args.file)
        print(f"Loaded file: {stats}")
    else:
        stats = load_data_from_directory(args.data_dir)
        print(f"Loading complete: {stats}") 