"""
Comprehensive Pydantic models for Tracker.gg Valorant API responses.
Generated from analysis of complete API endpoint capture.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ===============================
# ENUMS AND CONSTANTS
# ===============================

class DisplayType(str, Enum):
    """Display types for statistics."""
    NUMBER = "Number"
    NUMBER_PRECISION_1 = "NumberPrecision1"
    NUMBER_PRECISION_2 = "NumberPrecision2"
    NUMBER_PERCENTAGE = "NumberPercentage"
    TIME_SECONDS = "TimeSeconds"


class StatCategory(str, Enum):
    """Categories for statistics."""
    COMBAT = "combat"
    GAME = "game"


class SegmentType(str, Enum):
    """Types of segments available."""
    PLAYLIST = "playlist"
    LOADOUT = "loadout"
    MONTH_REPORT = "month-report"
    SEASON_REPORT = "season-report"


class Playlist(str, Enum):
    """Available playlists."""
    COMPETITIVE = "competitive"
    PREMIER = "premier"
    UNRATED = "unrated"
    DEATHMATCH = "deathmatch"
    TEAM_DEATHMATCH = "team-deathmatch"
    SPIKERUSH = "spikerush"
    SWIFTPLAY = "swiftplay"
    ESCALATION = "escalation"
    REPLICATION = "replication"
    SNOWBALL = "snowball"
    NEWMAP_SWIFTPLAY = "newmap-swiftplay"
    NEWMAP_BOMB = "newmap-bomb"


class LoadoutType(str, Enum):
    """Types of loadouts."""
    PISTOL = "pistol"
    SEMI = "semi"
    ECO = "eco"
    ANTI_ECO = "anti-eco"
    RIFLE = "rifle"
    HEAVY = "heavy"


# ===============================
# BASE COMPONENTS
# ===============================

class StatValue(BaseModel):
    """Individual statistic value with display information."""
    displayName: str = Field(..., description="Human-readable name of the statistic")
    displayCategory: str = Field(..., description="Display category for grouping")
    category: StatCategory = Field(..., description="Internal category")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    value: Union[int, float] = Field(..., description="Raw numerical value")
    displayValue: str = Field(..., description="Formatted display value")
    displayType: DisplayType = Field(..., description="How to display this value")
    description: Optional[str] = Field(None, description="Additional description")


class Metadata(BaseModel):
    """Metadata for segments and data objects."""
    name: str = Field(..., description="Display name")
    schema: str = Field(..., description="Schema version (e.g., 'statsv2')")


class Attributes(BaseModel):
    """Attributes for segments."""
    key: str = Field(..., description="Internal key identifier")
    playlist: Optional[Playlist] = Field(None, description="Associated playlist")
    seasonId: Optional[str] = Field(None, description="Season ID (null for current)")


class LoadoutAttributes(Attributes):
    """Attributes specific to loadout segments."""
    key: LoadoutType = Field(..., description="Loadout type")


# ===============================
# HEATMAP AND TIME-BASED DATA
# ===============================

class HeatmapValues(BaseModel):
    """Values for a single day in the heatmap."""
    playtime: int = Field(..., description="Playtime in milliseconds")
    kd: float = Field(..., description="Kill/Death ratio")
    placement: float = Field(..., description="Average placement")
    score: float = Field(..., description="Average score")
    kills: int = Field(..., description="Total kills")
    deaths: int = Field(..., description="Total deaths")
    hsAccuracy: float = Field(..., description="Headshot accuracy (deprecated, usually 0)")
    matches: int = Field(..., description="Number of matches")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    winPct: float = Field(..., description="Win percentage")
    adr: float = Field(..., description="Average damage per round")


class HeatmapEntry(BaseModel):
    """Single entry in the heatmap timeline."""
    date: datetime = Field(..., description="Date for this entry")
    values: HeatmapValues = Field(..., description="Statistics for this date")


# ===============================
# PARTY AND TEAMMATE DATA
# ===============================

class PartyData(BaseModel):
    """Statistics for a party member."""
    kd: float = Field(..., description="Kill/Death ratio")
    placement: float = Field(..., description="Average placement")
    matches: int = Field(..., description="Number of matches")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    winPct: float = Field(..., description="Win percentage")


class PartyMember(BaseModel):
    """Party member information."""
    party: int = Field(..., description="Party number")
    data: PartyData = Field(..., description="Statistics for this party member")


# ===============================
# COMPREHENSIVE STATS COLLECTIONS
# ===============================

class PlaylistStats(BaseModel):
    """Comprehensive statistics for playlist segments."""
    # Match Statistics
    matchesPlayed: StatValue
    matchesWon: StatValue
    matchesLost: StatValue
    matchesTied: StatValue
    matchesWinPct: StatValue
    matchesDisconnected: StatValue
    matchesDuration: StatValue
    timePlayed: StatValue
    mVPs: StatValue
    
    # Round Statistics
    roundsPlayed: StatValue
    roundsWon: StatValue
    roundsLost: StatValue
    roundsWinPct: StatValue
    roundsDuration: StatValue
    
    # Combat Statistics
    score: StatValue
    scorePerMatch: StatValue
    scorePerRound: StatValue
    kills: StatValue
    killsPerRound: StatValue
    killsPerMatch: StatValue
    deaths: StatValue
    deathsPerRound: StatValue
    deathsPerMatch: StatValue
    assists: StatValue
    assistsPerRound: StatValue
    assistsPerMatch: StatValue
    
    # Ratios
    kDRatio: StatValue
    kDARatio: StatValue
    kADRatio: StatValue
    
    # Damage Statistics
    damage: StatValue
    damageDelta: StatValue
    damageDeltaPerRound: StatValue
    damagePerRound: StatValue
    damagePerMatch: StatValue
    damagePerMinute: StatValue
    damageReceived: StatValue
    
    # Accuracy Statistics
    headshots: StatValue
    headshotsPerRound: StatValue
    headshotsPercentage: StatValue
    
    # Ability Statistics
    grenadeCasts: StatValue
    grenadeCastsPerRound: StatValue
    grenadeCastsPerMatch: StatValue
    ability1Casts: StatValue
    ability1CastsPerRound: StatValue
    ability1CastsPerMatch: StatValue
    ability2Casts: StatValue
    ability2CastsPerRound: StatValue
    ability2CastsPerMatch: StatValue
    ultimateCasts: StatValue
    ultimateCastsPerRound: StatValue
    ultimateCastsPerMatch: StatValue
    
    # Shot Statistics
    dealtHeadshots: StatValue
    dealtBodyshots: StatValue
    dealtLegshots: StatValue
    
    # Additional Statistics (dynamic based on available data)
    firstBloods: Optional[StatValue] = None
    firstDeaths: Optional[StatValue] = None
    survived: Optional[StatValue] = None
    traded: Optional[StatValue] = None
    kAST: Optional[StatValue] = None
    kasted: Optional[StatValue] = None
    esr: Optional[StatValue] = None


class LoadoutStats(BaseModel):
    """Statistics specific to loadout segments."""
    kills: StatValue
    deaths: StatValue
    kDRatio: StatValue
    assists: StatValue
    roundsPlayed: StatValue
    roundsWon: StatValue
    roundsLost: StatValue
    roundsWinPct: StatValue
    score: StatValue
    damage: StatValue
    damageReceived: StatValue
    headshots: StatValue
    headshotsPercentage: StatValue
    traded: StatValue
    survived: StatValue
    firstBloods: StatValue
    firstDeaths: StatValue
    esr: StatValue
    kAST: StatValue
    kasted: StatValue
    damagePerRound: StatValue
    scorePerRound: StatValue
    damageDelta: StatValue
    damageDeltaPerRound: StatValue


# ===============================
# SEGMENT DATA MODELS
# ===============================

class PlaylistSegment(BaseModel):
    """Playlist segment data structure."""
    type: SegmentType = Field(..., description="Segment type")
    attributes: Attributes = Field(..., description="Segment attributes")
    metadata: Metadata = Field(..., description="Segment metadata")
    expiryDate: datetime = Field(..., description="When this data expires")
    stats: PlaylistStats = Field(..., description="Comprehensive playlist statistics")


class LoadoutSegment(BaseModel):
    """Loadout segment data structure."""
    type: SegmentType = Field(..., description="Segment type")
    attributes: LoadoutAttributes = Field(..., description="Loadout-specific attributes")
    metadata: Metadata = Field(..., description="Segment metadata")
    expiryDate: datetime = Field(..., description="When this data expires")
    stats: LoadoutStats = Field(..., description="Loadout-specific statistics")


# ===============================
# AGGREGATED DATA MODELS
# ===============================

class AggregatedData(BaseModel):
    """Aggregated data from v1 API endpoints."""
    found: bool = Field(..., description="Whether data was found for this player")
    teammates: List[Any] = Field(default_factory=list, description="Teammate data (usually empty)")
    heatmap: List[HeatmapEntry] = Field(default_factory=list, description="Timeline heatmap data")
    parties: List[PartyMember] = Field(default_factory=list, description="Party member statistics")


# ===============================
# API RESPONSE MODELS
# ===============================

class V1AggregatedResponse(BaseModel):
    """Response structure for v1 aggregated endpoints."""
    data: AggregatedData = Field(..., description="Aggregated player data")


class V2PlaylistResponse(BaseModel):
    """Response structure for v2 playlist segment endpoints."""
    data: List[PlaylistSegment] = Field(..., description="List of playlist segments")


class V2LoadoutResponse(BaseModel):
    """Response structure for v2 loadout segment endpoints."""
    data: List[LoadoutSegment] = Field(..., description="List of loadout segments")


class V2SegmentResponse(BaseModel):
    """Generic response structure for v2 segment endpoints."""
    data: List[Union[PlaylistSegment, LoadoutSegment]] = Field(..., description="List of segments")


# ===============================
# UTILITY MODELS
# ===============================

class ErrorResponse(BaseModel):
    """Error response structure."""
    error: str = Field(..., description="Error message")
    status: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the error occurred")


class MetaResponse(BaseModel):
    """Metadata about the API response."""
    endpoint: str = Field(..., description="API endpoint called")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the request was made")
    username: str = Field(..., description="Target username")
    playlist: Optional[Playlist] = Field(None, description="Target playlist")
    success: bool = Field(..., description="Whether the request was successful")


# ===============================
# UNIFIED RESPONSE MODEL
# ===============================

class TrackerAPIResponse(BaseModel):
    """Unified response model for all tracker.gg API endpoints."""
    meta: MetaResponse = Field(..., description="Response metadata")
    data: Union[
        AggregatedData,
        List[PlaylistSegment],
        List[LoadoutSegment],
        List[Union[PlaylistSegment, LoadoutSegment]]
    ] = Field(..., description="Response data")
    error: Optional[ErrorResponse] = Field(None, description="Error information if request failed")


# ===============================
# ENHANCED MODELS FOR API INTEGRATION
# ===============================

class PremierData(BaseModel):
    """Specialized model for Premier playlist data."""
    playlist_stats: PlaylistSegment = Field(..., description="Premier playlist statistics")
    loadout_breakdown: List[LoadoutSegment] = Field(default_factory=list, description="Weapon loadout breakdown")
    
    @property
    def matches_played(self) -> int:
        """Get total matches played."""
        return self.playlist_stats.stats.matchesPlayed.value
    
    @property
    def win_rate(self) -> float:
        """Get win rate percentage."""
        return self.playlist_stats.stats.matchesWinPct.value
    
    @property
    def kd_ratio(self) -> float:
        """Get K/D ratio."""
        return self.playlist_stats.stats.kDRatio.value
    
    @property
    def average_combat_score(self) -> float:
        """Get average combat score (ACS)."""
        return self.playlist_stats.stats.scorePerRound.value


class ComprehensivePlayerStats(BaseModel):
    """Complete player statistics across all playlists."""
    username: str = Field(..., description="Player's riot ID")
    competitive: Optional[PlaylistSegment] = Field(None, description="Competitive stats")
    premier: Optional[PremierData] = Field(None, description="Premier stats with loadout breakdown")
    unrated: Optional[PlaylistSegment] = Field(None, description="Unrated stats")
    deathmatch: Optional[PlaylistSegment] = Field(None, description="Deathmatch stats")
    team_deathmatch: Optional[PlaylistSegment] = Field(None, description="Team Deathmatch stats")
    spike_rush: Optional[PlaylistSegment] = Field(None, description="Spike Rush stats")
    swift_play: Optional[PlaylistSegment] = Field(None, description="Swift Play stats")
    
    # Aggregated timeline data
    competitive_heatmap: List[HeatmapEntry] = Field(default_factory=list, description="Competitive timeline")
    premier_heatmap: List[HeatmapEntry] = Field(default_factory=list, description="Premier timeline")
    
    last_updated: datetime = Field(default_factory=datetime.now, description="When this data was last updated")


# ===============================
# REQUEST MODELS
# ===============================

class TrackerAPIRequest(BaseModel):
    """Request model for tracker.gg API calls."""
    username: str = Field(..., description="Riot ID (username#tag)")
    playlist: Optional[Playlist] = Field(None, description="Specific playlist to query")
    segment_type: Optional[SegmentType] = Field(None, description="Type of segment data to retrieve")
    season_id: Optional[str] = Field(None, description="Specific season ID (null for current)")
    source: Optional[str] = Field("web", description="Request source")
    include_heatmap: bool = Field(True, description="Whether to include heatmap/timeline data")
    include_loadouts: bool = Field(False, description="Whether to include loadout breakdown")


# ===============================
# CONFIGURATION MODEL
# ===============================

class TrackerAPIConfig(BaseModel):
    """Configuration for tracker.gg API integration."""
    flaresolverr_url: str = Field(..., description="FlareSolverr endpoint URL")
    base_api_url: str = Field("https://api.tracker.gg", description="Base tracker.gg API URL")
    session_timeout: int = Field(60, description="Session timeout in seconds")
    request_delay: float = Field(0.5, description="Delay between requests in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User agent string"
    )
    headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "dnt": "1",
            "origin": "https://tracker.gg",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site"
        },
        description="Default headers for requests"
    )


# ===============================
# EXAMPLE USAGE AND VALIDATION
# ===============================

def example_usage():
    """Example of how to use these models."""
    # Example request
    request = TrackerAPIRequest(
        username="apolloZ#sun",
        playlist=Playlist.PREMIER,
        segment_type=SegmentType.PLAYLIST,
        include_heatmap=True,
        include_loadouts=True
    )
    
    # Example configuration
    config = TrackerAPIConfig(
        flaresolverr_url="http://localhost:8191/v1",
        session_timeout=60,
        request_delay=0.5
    )
    
    return request, config


if __name__ == "__main__":
    # Validate models can be instantiated
    request, config = example_usage()
    print("✅ All models validated successfully!")
    print(f"📋 Request: {request.username} - {request.playlist}")
    print(f"🔧 Config: {config.flaresolverr_url}") 