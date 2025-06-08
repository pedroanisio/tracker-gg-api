"""
Shared database models and connection logic using SQLModel.
Used across both ingestion and API exposure modules.
"""

from typing import Optional, List, Any, Dict
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select, JSON, Column
from sqlalchemy import Index, text
import os
from pathlib import Path

# Import the Pydantic models that we'll extend
from .models import (
    Playlist, SegmentType, LoadoutType, StatCategory, DisplayType,
    PlaylistStats, LoadoutStats, StatValue, HeatmapEntry, PartyMember
)


# ===============================
# DATABASE CONNECTION
# ===============================

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://valorant_user:valorant_pass@localhost:5432/valorant_tracker"
)

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    """Get a database session."""
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """Create database tables."""
    SQLModel.metadata.create_all(engine)


def init_db():
    """Initialize the database with tables."""
    print("Creating database tables...")
    create_db_and_tables()
    print("Database tables created successfully!")


# ===============================
# DATABASE MODELS
# ===============================

class Player(SQLModel, table=True):
    """Player table to store unique riot IDs."""
    __tablename__ = "players"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    riot_id: str = Field(unique=True, index=True, description="Riot ID (username#tag)")
    username: str = Field(index=True, description="Username part of riot ID")
    tag: str = Field(description="Tag part of riot ID")
    first_seen: datetime = Field(default_factory=datetime.utcnow, description="When player was first added")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last time data was updated")
    
    __table_args__ = (
        Index('idx_player_riot_id', 'riot_id'),
        Index('idx_player_username', 'username'),
    )


class StatisticValue(SQLModel, table=True):
    """Individual statistic values from tracker.gg."""
    __tablename__ = "statistic_values"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign key to segment
    segment_id: int = Field(foreign_key="player_segments.id", index=True)
    
    # Statistic identification
    stat_name: str = Field(index=True, description="Internal stat name (e.g., 'kills', 'deaths')")
    display_name: str = Field(description="Human-readable name")
    display_category: str = Field(description="Display category for grouping")
    category: str = Field(description="Internal category (combat/game)")
    
    # Values
    value: float = Field(description="Raw numerical value")
    display_value: str = Field(description="Formatted display value")
    display_type: str = Field(description="How to display this value")
    
    # Optional fields
    description: Optional[str] = Field(None, description="Additional description")
    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    __table_args__ = (
        Index('idx_stat_segment_name', 'segment_id', 'stat_name'),
    )


class PlayerSegment(SQLModel, table=True):
    """Player segment data (playlist or loadout)."""
    __tablename__ = "player_segments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign key to player
    player_id: int = Field(foreign_key="players.id", index=True)
    
    # Segment information
    segment_type: str = Field(index=True, description="Type of segment (playlist/loadout)")
    segment_key: str = Field(index=True, description="Segment key (competitive/premier/pistol/etc)")
    playlist: Optional[str] = Field(None, description="Associated playlist if applicable")
    season_id: Optional[str] = Field(None, description="Season ID (null for current)")
    
    # Metadata
    schema_version: str = Field(description="Schema version (e.g., 'statsv2')")
    display_name: str = Field(description="Human-readable segment name")
    expiry_date: datetime = Field(description="When this data expires")
    
    # Timestamps
    captured_at: datetime = Field(default_factory=datetime.utcnow, description="When this data was captured")
    
    # Source information
    source_url: Optional[str] = Field(None, description="Original API URL")
    source_file: Optional[str] = Field(None, description="Source JSON file if loaded from file")
    
    __table_args__ = (
        Index('idx_segment_player_type', 'player_id', 'segment_type'),
        Index('idx_segment_player_key', 'player_id', 'segment_key'),
        Index('idx_segment_playlist', 'playlist'),
    )


class HeatmapData(SQLModel, table=True):
    """Timeline/heatmap data for players."""
    __tablename__ = "heatmap_data"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign key to player
    player_id: int = Field(foreign_key="players.id", index=True)
    
    # Heatmap information
    playlist: str = Field(index=True, description="Associated playlist")
    date: datetime = Field(index=True, description="Date for this entry")
    
    # Statistics for this date
    playtime: int = Field(description="Playtime in milliseconds")
    kd_ratio: float = Field(description="Kill/Death ratio")
    placement: float = Field(description="Average placement")
    score: float = Field(description="Average score")
    kills: int = Field(description="Total kills")
    deaths: int = Field(description="Total deaths")
    hs_accuracy: float = Field(description="Headshot accuracy")
    matches: int = Field(description="Number of matches")
    wins: int = Field(description="Number of wins")
    losses: int = Field(description="Number of losses")
    win_pct: float = Field(description="Win percentage")
    adr: float = Field(description="Average damage per round")
    
    # Timestamps
    captured_at: datetime = Field(default_factory=datetime.utcnow, description="When this data was captured")
    
    __table_args__ = (
        Index('idx_heatmap_player_playlist', 'player_id', 'playlist'),
        Index('idx_heatmap_date', 'date'),
    )


class PartyStatistic(SQLModel, table=True):
    """Party/teammate statistics."""
    __tablename__ = "party_statistics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign key to player
    player_id: int = Field(foreign_key="players.id", index=True)
    
    # Party information
    playlist: str = Field(index=True, description="Associated playlist")
    party_number: int = Field(description="Party identifier")
    
    # Statistics
    kd_ratio: float = Field(description="Kill/Death ratio")
    placement: float = Field(description="Average placement")
    matches: int = Field(description="Number of matches")
    wins: int = Field(description="Number of wins")
    losses: int = Field(description="Number of losses")
    win_pct: float = Field(description="Win percentage")
    
    # Timestamps
    captured_at: datetime = Field(default_factory=datetime.utcnow, description="When this data was captured")
    
    __table_args__ = (
        Index('idx_party_player_playlist', 'player_id', 'playlist'),
    )


class DataIngestionLog(SQLModel, table=True):
    """Log of data ingestion operations."""
    __tablename__ = "data_ingestion_log"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Operation details
    operation_type: str = Field(description="Type of operation (file_load, api_capture, etc.)")
    source: str = Field(description="Source of data (filename, URL, etc.)")
    player_riot_id: Optional[str] = Field(None, description="Riot ID if player-specific")
    
    # Results
    status: str = Field(description="Success/Error/Warning")
    records_processed: int = Field(default=0, description="Number of records processed")
    records_inserted: int = Field(default=0, description="Number of records inserted")
    records_updated: int = Field(default=0, description="Number of records updated")
    
    # Details
    details: Optional[str] = Field(None, description="Additional details or error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When operation started")
    completed_at: Optional[datetime] = Field(None, description="When operation completed")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")
    
    __table_args__ = (
        Index('idx_ingestion_type', 'operation_type'),
        Index('idx_ingestion_status', 'status'),
        Index('idx_ingestion_started', 'started_at'),
    )


# ===============================
# HELPER FUNCTIONS
# ===============================

def get_or_create_player(session: Session, riot_id: str) -> Player:
    """Get existing player or create new one."""
    # Try to find existing player
    stmt = select(Player).where(Player.riot_id == riot_id)
    player = session.exec(stmt).first()
    
    if player:
        # Update last_updated timestamp
        player.last_updated = datetime.utcnow()
        session.add(player)
        return player
    
    # Create new player
    username, tag = riot_id.split('#') if '#' in riot_id else (riot_id, '')
    player = Player(
        riot_id=riot_id,
        username=username,
        tag=tag
    )
    session.add(player)
    session.flush()  # Get the ID
    return player


def create_segment_with_stats(
    session: Session,
    player_id: int,
    segment_type: str,
    segment_key: str,
    stats_data: Dict[str, Any],
    metadata: Dict[str, Any],
    **kwargs
) -> PlayerSegment:
    """Create a segment with its associated statistics."""
    
    # Create the segment
    segment = PlayerSegment(
        player_id=player_id,
        segment_type=segment_type,
        segment_key=segment_key,
        **kwargs
    )
    session.add(segment)
    session.flush()  # Get the ID
    
    # Add all statistics
    for stat_name, stat_data in stats_data.items():
        if isinstance(stat_data, dict) and 'value' in stat_data:
            stat_value = StatisticValue(
                segment_id=segment.id,
                stat_name=stat_name,
                display_name=stat_data.get('displayName', stat_name),
                display_category=stat_data.get('displayCategory', ''),
                category=stat_data.get('category', ''),
                value=float(stat_data['value']),
                display_value=stat_data.get('displayValue', str(stat_data['value'])),
                display_type=stat_data.get('displayType', 'Number'),
                description=stat_data.get('description'),
                metadata=stat_data.get('metadata', {})
            )
            session.add(stat_value)
    
    return segment


def get_player_stats_summary(session: Session, riot_id: str) -> Dict[str, Any]:
    """Get a summary of player statistics across all segments."""
    
    # Get player
    stmt = select(Player).where(Player.riot_id == riot_id)
    player = session.exec(stmt).first()
    
    if not player:
        return {"error": "Player not found"}
    
    # Get all segments
    segments_stmt = select(PlayerSegment).where(PlayerSegment.player_id == player.id)
    segments = session.exec(segments_stmt).all()
    
    # Group by playlist
    playlists = {}
    for segment in segments:
        if segment.segment_type == "playlist":
            playlist_name = segment.playlist or segment.segment_key
            if playlist_name not in playlists:
                playlists[playlist_name] = {
                    "segment_id": segment.id,
                    "display_name": segment.display_name,
                    "captured_at": segment.captured_at,
                    "stats": {}
                }
            
            # Get stats for this segment
            stats_stmt = select(StatisticValue).where(StatisticValue.segment_id == segment.id)
            stats = session.exec(stats_stmt).all()
            
            for stat in stats:
                playlists[playlist_name]["stats"][stat.stat_name] = {
                    "value": stat.value,
                    "display_value": stat.display_value,
                    "display_name": stat.display_name
                }
    
    return {
        "player": {
            "riot_id": player.riot_id,
            "username": player.username,
            "tag": player.tag,
            "last_updated": player.last_updated
        },
        "playlists": playlists,
        "total_segments": len(segments)
    }


def log_ingestion_operation(
    session: Session,
    operation_type: str,
    source: str,
    status: str,
    player_riot_id: Optional[str] = None,
    records_processed: int = 0,
    records_inserted: int = 0,
    records_updated: int = 0,
    details: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    started_at: Optional[datetime] = None
) -> DataIngestionLog:
    """Log a data ingestion operation."""
    
    now = datetime.utcnow()
    if started_at is None:
        started_at = now
    
    duration = (now - started_at).total_seconds()
    
    log_entry = DataIngestionLog(
        operation_type=operation_type,
        source=source,
        player_riot_id=player_riot_id,
        status=status,
        records_processed=records_processed,
        records_inserted=records_inserted,
        records_updated=records_updated,
        details=details,
        metadata=metadata or {},
        started_at=started_at,
        completed_at=now,
        duration_seconds=duration
    )
    
    session.add(log_entry)
    return log_entry


# ===============================
# DATABASE QUERIES
# ===============================

def get_premier_data(session: Session, riot_id: str) -> Optional[Dict[str, Any]]:
    """Get Premier-specific data for a player."""
    
    # Get player
    stmt = select(Player).where(Player.riot_id == riot_id)
    player = session.exec(stmt).first()
    
    if not player:
        return None
    
    # Get Premier playlist segment
    segments_stmt = select(PlayerSegment).where(
        PlayerSegment.player_id == player.id,
        PlayerSegment.playlist == "premier"
    )
    premier_segment = session.exec(segments_stmt).first()
    
    if not premier_segment:
        return None
    
    # Get Premier statistics
    stats_stmt = select(StatisticValue).where(StatisticValue.segment_id == premier_segment.id)
    stats = session.exec(stats_stmt).all()
    
    # Get Premier heatmap data
    heatmap_stmt = select(HeatmapData).where(
        HeatmapData.player_id == player.id,
        HeatmapData.playlist == "premier"
    ).order_by(HeatmapData.date.desc()).limit(30)  # Last 30 days
    heatmap_data = session.exec(heatmap_stmt).all()
    
    # Format response
    stats_dict = {}
    for stat in stats:
        stats_dict[stat.stat_name] = {
            "value": stat.value,
            "display_value": stat.display_value,
            "display_name": stat.display_name,
            "category": stat.category
        }
    
    heatmap_list = []
    for entry in heatmap_data:
        heatmap_list.append({
            "date": entry.date.isoformat(),
            "kills": entry.kills,
            "deaths": entry.deaths,
            "kd_ratio": entry.kd_ratio,
            "matches": entry.matches,
            "wins": entry.wins,
            "win_pct": entry.win_pct,
            "adr": entry.adr
        })
    
    return {
        "player": {
            "riot_id": player.riot_id,
            "username": player.username,
            "tag": player.tag
        },
        "premier_stats": stats_dict,
        "recent_performance": heatmap_list,
        "last_updated": premier_segment.captured_at.isoformat()
    }


def get_all_playlists(session: Session, riot_id: str) -> Optional[Dict[str, Any]]:
    """Get all playlist data for a player."""
    
    # Get player
    stmt = select(Player).where(Player.riot_id == riot_id)
    player = session.exec(stmt).first()
    
    if not player:
        return None
    
    # Get all playlist segments
    segments_stmt = select(PlayerSegment).where(
        PlayerSegment.player_id == player.id,
        PlayerSegment.segment_type == "playlist"
    )
    segments = session.exec(segments_stmt).all()
    
    playlists = {}
    for segment in segments:
        playlist_name = segment.playlist or segment.segment_key
        
        # Get stats for this segment
        stats_stmt = select(StatisticValue).where(StatisticValue.segment_id == segment.id)
        stats = session.exec(stats_stmt).all()
        
        stats_dict = {}
        for stat in stats:
            stats_dict[stat.stat_name] = {
                "value": stat.value,
                "display_value": stat.display_value,
                "display_name": stat.display_name
            }
        
        playlists[playlist_name] = {
            "stats": stats_dict,
            "display_name": segment.display_name,
            "captured_at": segment.captured_at.isoformat()
        }
    
    return {
        "player": {
            "riot_id": player.riot_id,
            "username": player.username,
            "tag": player.tag,
            "last_updated": player.last_updated.isoformat()
        },
        "playlists": playlists
    } 