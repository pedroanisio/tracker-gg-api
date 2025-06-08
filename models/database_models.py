"""
SQLModel database models for storing tracker.gg Valorant data in PostgreSQL.
SQLModel combines SQLAlchemy ORM with Pydantic validation, allowing us to reuse 
our existing Pydantic models while adding database functionality.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index


# ===============================
# DATABASE MODELS USING SQLMODEL
# ===============================

class PlayerBase(SQLModel):
    """Base player model with shared fields."""
    riot_id: str = Field(unique=True, index=True, max_length=100)  # username#tag
    username: str = Field(max_length=50)
    tag: str = Field(max_length=10)


class Player(PlayerBase, table=True):
    """Player table model."""
    __tablename__ = "players"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    playlist_stats: List["PlaylistStats"] = Relationship(back_populates="player")
    loadout_stats: List["LoadoutStats"] = Relationship(back_populates="player")
    heatmap_entries: List["HeatmapEntry"] = Relationship(back_populates="player")


class PlayerRead(PlayerBase):
    """Player model for API responses."""
    id: int
    created_at: datetime
    updated_at: datetime


class PlayerCreate(PlayerBase):
    """Player model for creation."""
    pass


class PlaylistStatsBase(SQLModel):
    """Base playlist statistics model."""
    playlist: str = Field(index=True, max_length=50)
    season_id: Optional[str] = Field(default=None, max_length=100)
    source: str = Field(default="web", max_length=20)
    
    # Match Statistics
    matches_played: int = Field(default=0)
    matches_won: int = Field(default=0)
    matches_lost: int = Field(default=0)
    matches_tied: int = Field(default=0)
    matches_win_pct: float = Field(default=0.0)
    matches_disconnected: int = Field(default=0)
    matches_duration: float = Field(default=0.0)  # seconds
    time_played: int = Field(default=0)  # seconds
    mvps: int = Field(default=0)
    
    # Round Statistics
    rounds_played: int = Field(default=0)
    rounds_won: int = Field(default=0)
    rounds_lost: int = Field(default=0)
    rounds_win_pct: float = Field(default=0.0)
    rounds_duration: float = Field(default=0.0)
    
    # Combat Statistics
    score: int = Field(default=0)
    score_per_match: float = Field(default=0.0)
    score_per_round: float = Field(default=0.0)  # ACS
    kills: int = Field(default=0)
    kills_per_round: float = Field(default=0.0)
    kills_per_match: float = Field(default=0.0)
    deaths: int = Field(default=0)
    deaths_per_round: float = Field(default=0.0)
    deaths_per_match: float = Field(default=0.0)
    assists: int = Field(default=0)
    assists_per_round: float = Field(default=0.0)
    assists_per_match: float = Field(default=0.0)
    
    # Ratios
    kd_ratio: float = Field(default=0.0)
    kda_ratio: float = Field(default=0.0)
    kad_ratio: float = Field(default=0.0)
    
    # Damage Statistics
    damage: int = Field(default=0)
    damage_delta: int = Field(default=0)
    damage_delta_per_round: float = Field(default=0.0)
    damage_per_round: float = Field(default=0.0)  # ADR
    damage_per_match: float = Field(default=0.0)
    damage_per_minute: float = Field(default=0.0)
    damage_received: int = Field(default=0)
    
    # Accuracy Statistics
    headshots: int = Field(default=0)
    headshots_per_round: float = Field(default=0.0)
    headshots_percentage: float = Field(default=0.0)
    
    # Ability Statistics
    grenade_casts: int = Field(default=0)
    grenade_casts_per_round: float = Field(default=0.0)
    grenade_casts_per_match: float = Field(default=0.0)
    ability1_casts: int = Field(default=0)
    ability1_casts_per_round: float = Field(default=0.0)
    ability1_casts_per_match: float = Field(default=0.0)
    ability2_casts: int = Field(default=0)
    ability2_casts_per_round: float = Field(default=0.0)
    ability2_casts_per_match: float = Field(default=0.0)
    ultimate_casts: int = Field(default=0)
    ultimate_casts_per_round: float = Field(default=0.0)
    ultimate_casts_per_match: float = Field(default=0.0)
    
    # Shot Statistics
    dealt_headshots: int = Field(default=0)
    dealt_bodyshots: int = Field(default=0)
    dealt_legshots: int = Field(default=0)
    
    # Additional Statistics (optional)
    first_bloods: Optional[int] = Field(default=None)
    first_deaths: Optional[int] = Field(default=None)
    survived: Optional[int] = Field(default=None)
    traded: Optional[int] = Field(default=None)
    kast: Optional[float] = Field(default=None)
    kasted: Optional[int] = Field(default=None)
    esr: Optional[float] = Field(default=None)
    
    # Metadata
    expiry_date: Optional[datetime] = Field(default=None)


class PlaylistStats(PlaylistStatsBase, table=True):
    """Playlist statistics table model."""
    __tablename__ = "playlist_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="players.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Store original JSON for reference
    raw_data: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    
    # Relationships
    player: Player = Relationship(back_populates="playlist_stats")


class PlaylistStatsRead(PlaylistStatsBase):
    """Playlist statistics for API responses."""
    id: int
    player_id: int
    created_at: datetime
    updated_at: datetime


class PlaylistStatsCreate(PlaylistStatsBase):
    """Playlist statistics for creation."""
    player_id: int


class LoadoutStatsBase(SQLModel):
    """Base loadout statistics model."""
    playlist: str = Field(index=True, max_length=50)
    loadout_type: str = Field(max_length=20)  # pistol, rifle, etc.
    season_id: Optional[str] = Field(default=None, max_length=100)
    
    # Combat Statistics
    kills: int = Field(default=0)
    deaths: int = Field(default=0)
    kd_ratio: float = Field(default=0.0)
    assists: int = Field(default=0)
    rounds_played: int = Field(default=0)
    rounds_won: int = Field(default=0)
    rounds_lost: int = Field(default=0)
    rounds_win_pct: float = Field(default=0.0)
    score: int = Field(default=0)
    damage: int = Field(default=0)
    damage_received: int = Field(default=0)
    headshots: int = Field(default=0)
    headshots_percentage: float = Field(default=0.0)
    traded: int = Field(default=0)
    survived: int = Field(default=0)
    first_bloods: int = Field(default=0)
    first_deaths: int = Field(default=0)
    esr: float = Field(default=0.0)
    kast: float = Field(default=0.0)
    kasted: int = Field(default=0)
    damage_per_round: float = Field(default=0.0)
    score_per_round: float = Field(default=0.0)
    damage_delta: int = Field(default=0)
    damage_delta_per_round: float = Field(default=0.0)
    
    # Metadata
    expiry_date: Optional[datetime] = Field(default=None)


class LoadoutStats(LoadoutStatsBase, table=True):
    """Loadout statistics table model."""
    __tablename__ = "loadout_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="players.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Store original JSON for reference
    raw_data: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    
    # Relationships
    player: Player = Relationship(back_populates="loadout_stats")


class LoadoutStatsRead(LoadoutStatsBase):
    """Loadout statistics for API responses."""
    id: int
    player_id: int
    created_at: datetime
    updated_at: datetime


class LoadoutStatsCreate(LoadoutStatsBase):
    """Loadout statistics for creation."""
    player_id: int


class HeatmapEntryBase(SQLModel):
    """Base heatmap entry model."""
    playlist: str = Field(index=True, max_length=50)
    date: datetime = Field(index=True)
    
    # Performance metrics
    playtime: int = Field(default=0)  # milliseconds
    kd: float = Field(default=0.0)
    placement: float = Field(default=0.0)
    score: float = Field(default=0.0)
    kills: int = Field(default=0)
    deaths: int = Field(default=0)
    hs_accuracy: float = Field(default=0.0)
    matches: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    win_pct: float = Field(default=0.0)
    adr: float = Field(default=0.0)


class HeatmapEntry(HeatmapEntryBase, table=True):
    """Heatmap entry table model."""
    __tablename__ = "heatmap_entries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="players.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    player: Player = Relationship(back_populates="heatmap_entries")


class HeatmapEntryRead(HeatmapEntryBase):
    """Heatmap entry for API responses."""
    id: int
    player_id: int
    created_at: datetime


class HeatmapEntryCreate(HeatmapEntryBase):
    """Heatmap entry for creation."""
    player_id: int


class RawApiResponseBase(SQLModel):
    """Base raw API response model."""
    endpoint_type: str = Field(index=True, max_length=50)
    player_riot_id: str = Field(index=True, max_length=100)
    playlist: Optional[str] = Field(default=None, index=True, max_length=50)
    season_id: Optional[str] = Field(default=None, max_length=100)
    source: str = Field(default="web", max_length=20)
    
    success: bool = Field(default=True)
    error_message: Optional[str] = Field(default=None)
    file_name: Optional[str] = Field(default=None, max_length=255)
    segment_type: Optional[str] = Field(default=None, max_length=30)
    loadout_type: Optional[str] = Field(default=None, max_length=20)


class RawApiResponse(RawApiResponseBase, table=True):
    """Raw API response table model."""
    __tablename__ = "raw_api_responses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    response_data: dict = Field(sa_column=Column(JSONB))
    captured_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RawApiResponseRead(RawApiResponseBase):
    """Raw API response for API responses."""
    id: int
    response_data: dict
    captured_at: datetime


class RawApiResponseCreate(RawApiResponseBase):
    """Raw API response for creation."""
    response_data: dict


# ===============================
# CONVERSION UTILITIES
# ===============================

def convert_pydantic_to_sqlmodel(pydantic_data, target_model_class):
    """Convert Pydantic model data to SQLModel for database storage."""
    # Extract fields that exist in both models
    target_fields = target_model_class.__fields__.keys()
    converted_data = {}
    
    for field_name in target_fields:
        if hasattr(pydantic_data, field_name):
            converted_data[field_name] = getattr(pydantic_data, field_name)
    
    return target_model_class(**converted_data)


def convert_tracker_playlist_to_db(tracker_segment, player_id: int) -> PlaylistStatsCreate:
    """Convert tracker.gg playlist segment to database model."""
    stats = tracker_segment.stats
    
    return PlaylistStatsCreate(
        player_id=player_id,
        playlist=tracker_segment.attributes.playlist,
        season_id=tracker_segment.attributes.seasonId,
        
        # Match Statistics
        matches_played=stats.matchesPlayed.value,
        matches_won=stats.matchesWon.value,
        matches_lost=stats.matchesLost.value,
        matches_tied=stats.matchesTied.value,
        matches_win_pct=stats.matchesWinPct.value,
        matches_disconnected=stats.matchesDisconnected.value,
        matches_duration=stats.matchesDuration.value,
        time_played=stats.timePlayed.value,
        mvps=stats.mVPs.value,
        
        # Round Statistics
        rounds_played=stats.roundsPlayed.value,
        rounds_won=stats.roundsWon.value,
        rounds_lost=stats.roundsLost.value,
        rounds_win_pct=stats.roundsWinPct.value,
        rounds_duration=stats.roundsDuration.value,
        
        # Combat Statistics
        score=stats.score.value,
        score_per_match=stats.scorePerMatch.value,
        score_per_round=stats.scorePerRound.value,
        kills=stats.kills.value,
        kills_per_round=stats.killsPerRound.value,
        kills_per_match=stats.killsPerMatch.value,
        deaths=stats.deaths.value,
        deaths_per_round=stats.deathsPerRound.value,
        deaths_per_match=stats.deathsPerMatch.value,
        assists=stats.assists.value,
        assists_per_round=stats.assistsPerRound.value,
        assists_per_match=stats.assistsPerMatch.value,
        
        # Ratios
        kd_ratio=stats.kDRatio.value,
        kda_ratio=stats.kDARatio.value,
        kad_ratio=stats.kADRatio.value,
        
        # Damage Statistics
        damage=stats.damage.value,
        damage_delta=stats.damageDelta.value,
        damage_delta_per_round=stats.damageDeltaPerRound.value,
        damage_per_round=stats.damagePerRound.value,
        damage_per_match=stats.damagePerMatch.value,
        damage_per_minute=stats.damagePerMinute.value,
        damage_received=stats.damageReceived.value,
        
        # Accuracy Statistics
        headshots=stats.headshots.value,
        headshots_per_round=stats.headshotsPerRound.value,
        headshots_percentage=stats.headshotsPercentage.value,
        
        # Ability Statistics
        grenade_casts=stats.grenadeCasts.value,
        grenade_casts_per_round=stats.grenadeCastsPerRound.value,
        grenade_casts_per_match=stats.grenadeCastsPerMatch.value,
        ability1_casts=stats.ability1Casts.value,
        ability1_casts_per_round=stats.ability1CastsPerRound.value,
        ability1_casts_per_match=stats.ability1CastsPerMatch.value,
        ability2_casts=stats.ability2Casts.value,
        ability2_casts_per_round=stats.ability2CastsPerRound.value,
        ability2_casts_per_match=stats.ability2CastsPerMatch.value,
        ultimate_casts=stats.ultimateCasts.value,
        ultimate_casts_per_round=stats.ultimateCastsPerRound.value,
        ultimate_casts_per_match=stats.ultimateCastsPerMatch.value,
        
        # Shot Statistics
        dealt_headshots=stats.dealtHeadshots.value,
        dealt_bodyshots=stats.dealtBodyshots.value,
        dealt_legshots=stats.dealtLegshots.value,
        
        # Optional Statistics
        first_bloods=stats.firstBloods.value if stats.firstBloods else None,
        first_deaths=stats.firstDeaths.value if stats.firstDeaths else None,
        survived=stats.survived.value if stats.survived else None,
        traded=stats.traded.value if stats.traded else None,
        kast=stats.kAST.value if stats.kAST else None,
        kasted=stats.kasted.value if stats.kasted else None,
        esr=stats.esr.value if stats.esr else None,
        
        expiry_date=tracker_segment.expiryDate if tracker_segment.expiryDate.year > 1 else None
    )


def convert_tracker_loadout_to_db(loadout_segment, player_id: int) -> LoadoutStatsCreate:
    """Convert tracker.gg loadout segment to database model."""
    stats = loadout_segment.stats
    
    return LoadoutStatsCreate(
        player_id=player_id,
        playlist=loadout_segment.attributes.playlist,
        loadout_type=loadout_segment.attributes.key,
        season_id=loadout_segment.attributes.seasonId,
        
        kills=stats.kills.value,
        deaths=stats.deaths.value,
        kd_ratio=stats.kDRatio.value,
        assists=stats.assists.value,
        rounds_played=stats.roundsPlayed.value,
        rounds_won=stats.roundsWon.value,
        rounds_lost=stats.roundsLost.value,
        rounds_win_pct=stats.roundsWinPct.value,
        score=stats.score.value,
        damage=stats.damage.value,
        damage_received=stats.damageReceived.value,
        headshots=stats.headshots.value,
        headshots_percentage=stats.headshotsPercentage.value,
        traded=stats.traded.value,
        survived=stats.survived.value,
        first_bloods=stats.firstBloods.value,
        first_deaths=stats.firstDeaths.value,
        esr=stats.esr.value,
        kast=stats.kAST.value,
        kasted=stats.kasted.value,
        damage_per_round=stats.damagePerRound.value,
        score_per_round=stats.scorePerRound.value,
        damage_delta=stats.damageDelta.value,
        damage_delta_per_round=stats.damageDeltaPerRound.value,
        
        expiry_date=loadout_segment.expiryDate if loadout_segment.expiryDate.year > 1 else None
    )


def convert_heatmap_entry_to_db(heatmap_entry, player_id: int, playlist: str) -> HeatmapEntryCreate:
    """Convert tracker.gg heatmap entry to database model."""
    return HeatmapEntryCreate(
        player_id=player_id,
        playlist=playlist,
        date=heatmap_entry.date,
        playtime=heatmap_entry.values.playtime,
        kd=heatmap_entry.values.kd,
        placement=heatmap_entry.values.placement,
        score=heatmap_entry.values.score,
        kills=heatmap_entry.values.kills,
        deaths=heatmap_entry.values.deaths,
        hs_accuracy=heatmap_entry.values.hsAccuracy,
        matches=heatmap_entry.values.matches,
        wins=heatmap_entry.values.wins,
        losses=heatmap_entry.values.losses,
        win_pct=heatmap_entry.values.winPct,
        adr=heatmap_entry.values.adr
    )


# ===============================
# DATABASE CONFIGURATION
# ===============================

def get_database_url():
    """Get database URL from environment."""
    import os
    return os.getenv("DATABASE_URL", "postgresql://username:password@localhost:5432/valorant_tracker")


def create_db_and_tables(engine):
    """Create database tables and indexes."""
    SQLModel.metadata.create_all(engine)
    
    # Add custom indexes for better performance
    from sqlalchemy import text
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_playlist_stats_player_playlist ON playlist_stats(player_id, playlist);",
        "CREATE INDEX IF NOT EXISTS idx_playlist_stats_playlist_season ON playlist_stats(playlist, season_id);",
        "CREATE INDEX IF NOT EXISTS idx_loadout_stats_player_playlist_loadout ON loadout_stats(player_id, playlist, loadout_type);",
        "CREATE INDEX IF NOT EXISTS idx_heatmap_entries_player_playlist_date ON heatmap_entries(player_id, playlist, date);",
        "CREATE INDEX IF NOT EXISTS idx_heatmap_entries_date_range ON heatmap_entries(date DESC);",
        "CREATE INDEX IF NOT EXISTS idx_raw_api_responses_player_endpoint ON raw_api_responses(player_riot_id, endpoint_type);",
        "CREATE INDEX IF NOT EXISTS idx_raw_api_responses_captured_at ON raw_api_responses(captured_at DESC);"
    ]
    
    with engine.connect() as conn:
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                conn.commit()
            except Exception as e:
                print(f"Warning: Could not create index: {e}")


# ===============================
# API RESPONSE MODELS
# ===============================

class PlayerWithStats(PlayerRead):
    """Player with all related statistics."""
    playlist_stats: List[PlaylistStatsRead] = []
    loadout_stats: List[LoadoutStatsRead] = []
    heatmap_entries: List[HeatmapEntryRead] = []


class PremierStatsResponse(SQLModel):
    """Specialized response for Premier statistics."""
    player: PlayerRead
    playlist_stats: PlaylistStatsRead
    loadout_stats: List[LoadoutStatsRead] = []
    heatmap_entries: List[HeatmapEntryRead] = []
    
    # Convenience properties
    @property
    def matches_played(self) -> int:
        return self.playlist_stats.matches_played
    
    @property
    def win_rate(self) -> float:
        return self.playlist_stats.matches_win_pct
    
    @property
    def kd_ratio(self) -> float:
        return self.playlist_stats.kd_ratio
    
    @property
    def acs(self) -> float:
        return self.playlist_stats.score_per_round 