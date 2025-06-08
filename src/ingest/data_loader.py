"""
Data loader for ingesting captured tracker.gg JSON files into the database.
Processes all JSON files from data capture and loads them into PostgreSQL.
"""

import os
import json
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlmodel import Session, select
import logging

# Import from shared modules
from ..shared.database import (
    engine, get_or_create_player, create_segment_with_stats, 
    log_ingestion_operation, Player, PlayerSegment, StatisticValue,
    HeatmapData, PartyStatistic, init_db
)
from ..shared.models import (
    V1AggregatedResponse, V2PlaylistResponse, V2LoadoutResponse,
    HeatmapEntry, PartyMember, PlaylistSegment, LoadoutSegment
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrackerDataLoader:
    """Loads tracker.gg API data from JSON files into the database."""
    
    def __init__(self, data_directory: str = "./data"):
        """
        Initialize the data loader.
        
        Args:
            data_directory: Directory containing JSON files to load
        """
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
        """
        Load all JSON files from the data directory.
        
        Returns:
            Summary statistics of the loading operation
        """
        
        # Initialize database
        init_db()
        
        # Find all JSON files
        json_files = list(self.data_directory.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {self.data_directory}")
            return self.stats
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        # Process each file
        with Session(engine) as session:
            for json_file in json_files:
                try:
                    self.load_file(session, json_file)
                    self.stats["files_successful"] += 1
                    logger.info(f"✓ Loaded {json_file.name}")
                except Exception as e:
                    self.stats["files_failed"] += 1
                    logger.error(f"✗ Failed to load {json_file.name}: {e}")
                    
                    # Log the failure
                    log_ingestion_operation(
                        session=session,
                        operation_type="file_load",
                        source=str(json_file),
                        status="error",
                        details=str(e)
                    )
                
                self.stats["files_processed"] += 1
            
            # Commit all changes
            session.commit()
        
        logger.info(f"Loading complete. Processed {self.stats['files_processed']} files")
        logger.info(f"Success: {self.stats['files_successful']}, Failed: {self.stats['files_failed']}")
        logger.info(f"Created: {self.stats['players_created']} players, {self.stats['segments_created']} segments")
        
        return self.stats
    
    def load_file(self, session: Session, file_path: Path) -> None:
        """
        Load a single JSON file into the database.
        
        Args:
            session: Database session
            file_path: Path to the JSON file
        """
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract riot_id from the data or filename
        riot_id = data.get("riot_id")
        if not riot_id:
            # Try to extract from filename (format: capture_username_tag_timestamp.json)
            filename = file_path.stem
            if filename.startswith("capture_"):
                parts = filename.split("_")
                if len(parts) >= 3:
                    riot_id = f"{parts[1]}#{parts[2]}"
        
        if not riot_id:
            raise ValueError(f"Could not determine riot_id from file {file_path}")
        
        # Get or create player
        player = get_or_create_player(session, riot_id)
        if not hasattr(player, '_was_existing'):  # New player
            self.stats["players_created"] += 1
        
        # Check if this is the new direct API response format
        if "data" in data and "original_filename" in data:
            # This is a direct API response format
            self._load_direct_api_response(session, player.id, data, file_path)
        else:
            # Process old nested endpoints format
            endpoints = data.get("endpoints", {})
            
            for endpoint_name, endpoint_data in endpoints.items():
                if endpoint_data.get("status") != "success":
                    continue
                    
                api_data = endpoint_data.get("data", {})
                
                try:
                    if endpoint_name.startswith("v1_") and "aggregated" in endpoint_name:
                        self._load_v1_aggregated_data(session, player.id, endpoint_name, api_data, file_path)
                    elif endpoint_name.startswith("v2_") and "playlist" in endpoint_name:
                        self._load_v2_playlist_data(session, player.id, endpoint_name, api_data, file_path)
                    elif endpoint_name.startswith("v2_") and "loadout" in endpoint_name:
                        self._load_v2_loadout_data(session, player.id, endpoint_name, api_data, file_path)
                    else:
                        logger.warning(f"Unknown endpoint type: {endpoint_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to process endpoint {endpoint_name}: {e}")
                    continue
            
            # Log successful ingestion (old format)
            log_ingestion_operation(
                session=session,
                operation_type="file_load",
                source=str(file_path),
                player_riot_id=riot_id,
                status="success",
                records_processed=len(endpoints),
                records_inserted=self.stats["segments_created"],
                details=f"Loaded {len(endpoints)} endpoints"
            )

    def _load_direct_api_response(self, session: Session, player_id: int, 
                                 data: Dict[str, Any], source_file: Path) -> None:
        """Load data from direct API response format."""
        
        original_filename = data.get("original_filename", "")
        api_data = data.get("data", {})
        
        # Skip if no data found
        if not api_data.get("found", False):
            return
        
        # Determine endpoint type from original filename
        if "v1_aggregated" in original_filename:
            # Extract playlist from filename (e.g., "grammar_v1_aggregated_deathmatch_...")
            parts = original_filename.split("_")
            if len(parts) >= 3:
                playlist = parts[2]  # Should be like "deathmatch", "competitive", etc.
                endpoint_name = f"v1_{playlist}_aggregated"
                self._load_v1_aggregated_data(session, player_id, endpoint_name, {"data": api_data}, source_file)
        
        elif "v2_playlist" in original_filename:
            # Extract playlist from filename  
            parts = original_filename.split("_")
            if len(parts) >= 3:
                playlist = parts[2]
                endpoint_name = f"v2_{playlist}_playlist"
                self._load_v2_playlist_data(session, player_id, endpoint_name, api_data, source_file)
        
        elif "v2_loadout" in original_filename:
            # Loadout data
            endpoint_name = "v2_loadout"
            self._load_v2_loadout_data(session, player_id, endpoint_name, api_data, source_file)
        
        else:
            logger.warning(f"Unknown API response type from filename: {original_filename}")
        
        # Log successful ingestion (new format)
        log_ingestion_operation(
            session=session,
            operation_type="file_load",
            source=str(source_file),
            player_riot_id=data.get("riot_id"),
            status="success",
            records_processed=1,
            records_inserted=self.stats.get("segments_created", 0),
            details=f"Loaded direct API response: {original_filename}"
        )
    
    def _load_v1_aggregated_data(self, session: Session, player_id: int, 
                                endpoint_name: str, api_data: Dict[str, Any], 
                                source_file: Path) -> None:
        """Load V1 aggregated data (heatmaps, parties)."""
        
        # Extract playlist from endpoint name
        playlist = endpoint_name.replace("v1_", "").replace("_aggregated", "")
        
        data_section = api_data.get("data", {})
        
        # Load heatmap data
        heatmap_data = data_section.get("heatmap", [])
        for entry in heatmap_data:
            heatmap_entry = HeatmapData(
                player_id=player_id,
                playlist=playlist,
                date=datetime.fromisoformat(entry["date"].replace("Z", "+00:00")),
                playtime=entry["values"]["playtime"],
                kd_ratio=entry["values"]["kd"],
                placement=entry["values"]["placement"],
                score=entry["values"]["score"],
                kills=entry["values"]["kills"],
                deaths=entry["values"]["deaths"],
                hs_accuracy=entry["values"]["hsAccuracy"],
                matches=entry["values"]["matches"],
                wins=entry["values"]["wins"],
                losses=entry["values"]["losses"],
                win_pct=entry["values"]["winPct"],
                adr=entry["values"]["adr"]
            )
            session.add(heatmap_entry)
            self.stats["heatmap_entries"] += 1
        
        # Load party data
        parties_data = data_section.get("parties", [])
        for party in parties_data:
            party_stat = PartyStatistic(
                player_id=player_id,
                playlist=playlist,
                party_number=party["party"],
                kd_ratio=party["data"]["kd"],
                placement=party["data"]["placement"],
                matches=party["data"]["matches"],
                wins=party["data"]["wins"],
                losses=party["data"]["losses"],
                win_pct=party["data"]["winPct"]
            )
            session.add(party_stat)
            self.stats["party_entries"] += 1
    
    def _load_v2_playlist_data(self, session: Session, player_id: int,
                              endpoint_name: str, api_data: Dict[str, Any],
                              source_file: Path) -> None:
        """Load V2 playlist segment data."""
        
        # Extract playlist from endpoint name
        playlist = endpoint_name.replace("v2_", "").replace("_playlist", "")
        
        segments = api_data.get("data", [])
        
        for segment_data in segments:
            # Create segment
            segment = create_segment_with_stats(
                session=session,
                player_id=player_id,
                segment_type="playlist",
                segment_key=segment_data["attributes"]["key"],
                stats_data=segment_data["stats"],
                metadata=segment_data["metadata"],
                playlist=segment_data["attributes"].get("playlist"),
                season_id=segment_data["attributes"].get("seasonId"),
                schema_version=segment_data["metadata"]["schema"],
                display_name=segment_data["metadata"]["name"],
                expiry_date=datetime.fromisoformat(segment_data["expiryDate"].replace("Z", "+00:00")),
                source_url=endpoint_name,
                source_file=str(source_file)
            )
            
            self.stats["segments_created"] += 1
            self.stats["stats_created"] += len(segment_data["stats"])
    
    def _load_v2_loadout_data(self, session: Session, player_id: int,
                             endpoint_name: str, api_data: Dict[str, Any],
                             source_file: Path) -> None:
        """Load V2 loadout segment data."""
        
        segments = api_data.get("data", [])
        
        for segment_data in segments:
            # Create segment
            segment = create_segment_with_stats(
                session=session,
                player_id=player_id,
                segment_type="loadout",
                segment_key=segment_data["attributes"]["key"],
                stats_data=segment_data["stats"],
                metadata=segment_data["metadata"],
                playlist=segment_data["attributes"].get("playlist"),
                season_id=segment_data["attributes"].get("seasonId"),
                schema_version=segment_data["metadata"]["schema"],
                display_name=segment_data["metadata"]["name"],
                expiry_date=datetime.fromisoformat(segment_data["expiryDate"].replace("Z", "+00:00")),
                source_url=endpoint_name,
                source_file=str(source_file)
            )
            
            self.stats["segments_created"] += 1
            self.stats["stats_created"] += len(segment_data["stats"])
    
    def get_loading_stats(self) -> Dict[str, Any]:
        """Get current loading statistics."""
        return self.stats.copy()


def load_data_from_directory(data_dir: str = "./data") -> Dict[str, Any]:
    """
    Convenience function to load all data from a directory.
    
    Args:
        data_dir: Directory containing JSON files
        
    Returns:
        Loading statistics
    """
    
    loader = TrackerDataLoader(data_dir)
    return loader.load_all_files()


def load_single_file(file_path: str) -> Dict[str, Any]:
    """
    Load a single JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loading statistics
    """
    
    # Initialize database
    init_db()
    
    loader = TrackerDataLoader()
    
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
            
            # Log the failure
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
    
    parser = argparse.ArgumentParser(description="Load tracker.gg data into database")
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