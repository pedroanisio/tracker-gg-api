"""
FastAPI application for exposing tracker.gg Valorant data.
Provides REST endpoints for accessing ingested player statistics.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Optional, List, Dict, Any, AsyncGenerator
from pydantic import BaseModel
from pathlib import Path as PathLib
import logging
import json
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import from shared modules
from ..shared.database import (
    get_session, Player, PlayerSegment, StatisticValue, 
    HeatmapData, PartyStatistic, DataIngestionLog,
    get_premier_data, get_all_playlists, get_player_stats_summary
)
from ..shared.models import (
    Playlist, SegmentType, LoadoutType,
    PremierData, ComprehensivePlayerStats
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Tracker.gg Valorant API",
    description="REST API for accessing Valorant player statistics from tracker.gg",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Get the directory of this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Setup templates and static files
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# RESPONSE MODELS
# ===============================

class PlayerResponse(dict):
    """Response model for player data."""
    pass

class StatsResponse(dict):
    """Response model for statistics."""
    pass

class ErrorResponse(dict):
    """Response model for errors."""
    pass

# ===============================
# UTILITY FUNCTIONS
# ===============================

def validate_riot_id(riot_id: str) -> str:
    """Validate and normalize riot ID format."""
    if '#' not in riot_id:
        raise HTTPException(
            status_code=400, 
            detail="Invalid Riot ID format. Expected format: username#tag"
        )
    return riot_id

def get_player_or_404(session: Session, riot_id: str) -> Player:
    """Get player by riot ID or raise 404."""
    stmt = select(Player).where(Player.riot_id == riot_id)
    player = session.exec(stmt).first()
    
    if not player:
        raise HTTPException(
            status_code=404,
            detail=f"Player '{riot_id}' not found in database"
        )
    
    return player

# ===============================
# HEALTH AND INFO ENDPOINTS
# ===============================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Tracker.gg Valorant API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "dashboard": "/dashboard",
        "endpoints": {
            "health": "/health",
            "players": "/players",
            "premier": "/players/{riot_id}/premier",
            "stats": "/players/{riot_id}/stats",
            "playlists": "/players/{riot_id}/playlists",
            "dashboard": "/dashboard"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check(session: Session = Depends(get_session)):
    """Health check endpoint."""
    try:
        # Test database connection
        result = session.exec(select(Player).limit(1))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# ===============================
# WEB INTERFACE ENDPOINTS
# ===============================

@app.get("/dashboard", response_class=HTMLResponse, tags=["Web Interface"])
async def dashboard(request: Request):
    """Serve the web dashboard for viewing player stats."""
    return templates.TemplateResponse("index.html", {"request": request})

# ===============================
# PLAYER ENDPOINTS
# ===============================

@app.get("/players", tags=["Players"])
async def list_players(
    limit: int = Query(50, ge=1, le=1000, description="Number of players to return"),
    offset: int = Query(0, ge=0, description="Number of players to skip"),
    search: Optional[str] = Query(None, description="Search by username"),
    session: Session = Depends(get_session)
):
    """List all players in the database."""
    
    stmt = select(Player)
    
    # Add search filter
    if search:
        stmt = stmt.where(Player.username.ilike(f"%{search}%"))
    
    # Add pagination
    stmt = stmt.offset(offset).limit(limit)
    
    players = session.exec(stmt).all()
    
    # Count total players for pagination
    count_stmt = select(Player)
    if search:
        count_stmt = count_stmt.where(Player.username.ilike(f"%{search}%"))
    total = len(session.exec(count_stmt).all())
    
    return {
        "players": [
            {
                "riot_id": player.riot_id,
                "username": player.username,
                "tag": player.tag,
                "first_seen": player.first_seen.isoformat(),
                "last_updated": player.last_updated.isoformat()
            }
            for player in players
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }

@app.get("/players/{riot_id}", tags=["Players"])
async def get_player_info(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
    session: Session = Depends(get_session)
):
    """Get basic player information."""
    
    riot_id = validate_riot_id(riot_id)
    player = get_player_or_404(session, riot_id)
    
    # Get segment counts
    segments_stmt = select(PlayerSegment).where(PlayerSegment.player_id == player.id)
    segments = session.exec(segments_stmt).all()
    
    playlist_segments = [s for s in segments if s.segment_type == "playlist"]
    loadout_segments = [s for s in segments if s.segment_type == "loadout"]
    
    return {
        "riot_id": player.riot_id,
        "username": player.username,
        "tag": player.tag,
        "first_seen": player.first_seen.isoformat(),
        "last_updated": player.last_updated.isoformat(),
        "data_summary": {
            "total_segments": len(segments),
            "playlist_segments": len(playlist_segments),
            "loadout_segments": len(loadout_segments),
            "available_playlists": list(set(s.playlist for s in playlist_segments if s.playlist))
        }
    }

# ===============================
# PREMIER ENDPOINT (Primary Goal)
# ===============================

@app.get("/players/{riot_id}/premier", tags=["Premier"])
async def get_player_premier_data(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
    include_recent: bool = Query(True, description="Include recent performance data"),
    session: Session = Depends(get_session)
):
    """
    Get Premier playlist data for a player.
    This is the main endpoint that was requested.
    """
    
    riot_id = validate_riot_id(riot_id)
    
    premier_data = get_premier_data(session, riot_id)
    
    if not premier_data:
        raise HTTPException(
            status_code=404,
            detail=f"No Premier data found for player '{riot_id}'"
        )
    
    return premier_data

# ===============================
# STATISTICS ENDPOINTS
# ===============================

@app.get("/players/{riot_id}/stats", tags=["Statistics"])
async def get_player_stats_summary_endpoint(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
    session: Session = Depends(get_session)
):
    """Get a summary of all player statistics."""
    
    riot_id = validate_riot_id(riot_id)
    
    stats_summary = get_player_stats_summary(session, riot_id)
    
    if "error" in stats_summary:
        raise HTTPException(status_code=404, detail=stats_summary["error"])
    
    return stats_summary

@app.get("/players/{riot_id}/playlists", tags=["Statistics"])
async def get_player_playlists(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
    playlist: Optional[str] = Query(None, description="Filter by specific playlist"),
    session: Session = Depends(get_session)
):
    """Get all playlist data for a player."""
    
    riot_id = validate_riot_id(riot_id)
    
    all_playlists = get_all_playlists(session, riot_id)
    
    if not all_playlists:
        raise HTTPException(
            status_code=404,
            detail=f"No playlist data found for player '{riot_id}'"
        )
    
    # Filter by specific playlist if requested
    if playlist:
        playlists_data = all_playlists.get("playlists", {})
        if playlist not in playlists_data:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for playlist '{playlist}' for player '{riot_id}'"
            )
        
        return {
            "player": all_playlists["player"],
            "playlists": {playlist: playlists_data[playlist]}
        }
    
    return all_playlists

@app.get("/players/{riot_id}/playlists/{playlist_name}", tags=["Statistics"])
async def get_specific_playlist_data(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
    playlist_name: str = Path(..., description="Playlist name (competitive, premier, etc.)"),
    session: Session = Depends(get_session)
):
    """Get specific playlist data for a player."""
    
    riot_id = validate_riot_id(riot_id)
    player = get_player_or_404(session, riot_id)
    
    # Get playlist segment
    stmt = select(PlayerSegment).where(
        PlayerSegment.player_id == player.id,
        PlayerSegment.playlist == playlist_name
    )
    segment = session.exec(stmt).first()
    
    if not segment:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for playlist '{playlist_name}' for player '{riot_id}'"
        )
    
    # Get all statistics for this segment
    stats_stmt = select(StatisticValue).where(StatisticValue.segment_id == segment.id)
    stats = session.exec(stats_stmt).all()
    
    stats_dict = {}
    for stat in stats:
        stats_dict[stat.stat_name] = {
            "value": stat.value,
            "display_value": stat.display_value,
            "display_name": stat.display_name,
            "category": stat.category,
            "display_type": stat.display_type
        }
    
    return {
        "player": {
            "riot_id": player.riot_id,
            "username": player.username,
            "tag": player.tag
        },
        "playlist": playlist_name,
        "segment_info": {
            "display_name": segment.display_name,
            "segment_type": segment.segment_type,
            "season_id": segment.season_id,
            "captured_at": segment.captured_at.isoformat()
        },
        "stats": stats_dict
    }

# ===============================
# HEATMAP AND TIMELINE ENDPOINTS
# ===============================

@app.get("/players/{riot_id}/heatmap", tags=["Timeline"])
async def get_player_heatmap(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
    playlist: Optional[str] = Query(None, description="Filter by playlist"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    session: Session = Depends(get_session)
):
    """Get heatmap/timeline data for a player."""
    
    riot_id = validate_riot_id(riot_id)
    player = get_player_or_404(session, riot_id)
    
    stmt = select(HeatmapData).where(HeatmapData.player_id == player.id)
    
    if playlist:
        stmt = stmt.where(HeatmapData.playlist == playlist)
    
    # Get recent data
    stmt = stmt.order_by(HeatmapData.date.desc()).limit(days)
    heatmap_data = session.exec(stmt).all()
    
    if not heatmap_data:
        raise HTTPException(
            status_code=404,
            detail=f"No heatmap data found for player '{riot_id}'"
        )
    
    return {
        "player": {
            "riot_id": player.riot_id,
            "username": player.username,
            "tag": player.tag
        },
        "playlist_filter": playlist,
        "days_requested": days,
        "data": [
            {
                "date": entry.date.isoformat(),
                "playlist": entry.playlist,
                "stats": {
                    "kills": entry.kills,
                    "deaths": entry.deaths,
                    "kd_ratio": entry.kd_ratio,
                    "matches": entry.matches,
                    "wins": entry.wins,
                    "losses": entry.losses,
                    "win_pct": entry.win_pct,
                    "adr": entry.adr,
                    "playtime": entry.playtime,
                    "score": entry.score
                }
            }
            for entry in reversed(heatmap_data)  # Reverse to get chronological order
        ]
    }

# ===============================
# LOADOUT ENDPOINTS
# ===============================

@app.get("/players/{riot_id}/loadouts", tags=["Loadouts"])
async def get_player_loadouts(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
    loadout_type: Optional[str] = Query(None, description="Filter by loadout type"),
    session: Session = Depends(get_session)
):
    """Get loadout statistics for a player."""
    
    riot_id = validate_riot_id(riot_id)
    player = get_player_or_404(session, riot_id)
    
    stmt = select(PlayerSegment).where(
        PlayerSegment.player_id == player.id,
        PlayerSegment.segment_type == "loadout"
    )
    
    if loadout_type:
        stmt = stmt.where(PlayerSegment.segment_key == loadout_type)
    
    segments = session.exec(stmt).all()
    
    if not segments:
        raise HTTPException(
            status_code=404,
            detail=f"No loadout data found for player '{riot_id}'"
        )
    
    loadouts = {}
    for segment in segments:
        # Get stats for this loadout
        stats_stmt = select(StatisticValue).where(StatisticValue.segment_id == segment.id)
        stats = session.exec(stats_stmt).all()
        
        stats_dict = {}
        for stat in stats:
            stats_dict[stat.stat_name] = {
                "value": stat.value,
                "display_value": stat.display_value,
                "display_name": stat.display_name
            }
        
        loadouts[segment.segment_key] = {
            "display_name": segment.display_name,
            "stats": stats_dict,
            "captured_at": segment.captured_at.isoformat()
        }
    
    return {
        "player": {
            "riot_id": player.riot_id,
            "username": player.username,
            "tag": player.tag
        },
        "loadout_filter": loadout_type,
        "loadouts": loadouts
    }

# ===============================
# ADMIN/DEBUG ENDPOINTS
# ===============================

@app.get("/admin/ingestion-logs", tags=["Admin"])
async def get_ingestion_logs(
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status"),
    session: Session = Depends(get_session)
):
    """Get data ingestion logs (admin endpoint)."""
    
    stmt = select(DataIngestionLog)
    
    if status:
        stmt = stmt.where(DataIngestionLog.status == status)
    
    stmt = stmt.order_by(DataIngestionLog.started_at.desc()).limit(limit)
    logs = session.exec(stmt).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "operation_type": log.operation_type,
                "source": log.source,
                "player_riot_id": log.player_riot_id,
                "status": log.status,
                "records_processed": log.records_processed,
                "records_inserted": log.records_inserted,
                "started_at": log.started_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "duration_seconds": log.duration_seconds,
                "details": log.details
            }
            for log in logs
        ]
    }

@app.get("/admin/stats", tags=["Admin"])
async def get_database_stats(session: Session = Depends(get_session)):
    """Get database statistics (admin endpoint)."""
    
    player_count = len(session.exec(select(Player)).all())
    segment_count = len(session.exec(select(PlayerSegment)).all())
    stat_count = len(session.exec(select(StatisticValue)).all())
    heatmap_count = len(session.exec(select(HeatmapData)).all())
    
    return {
        "database_stats": {
            "total_players": player_count,
            "total_segments": segment_count,
            "total_statistics": stat_count,
            "total_heatmap_entries": heatmap_count
        },
        "generated_at": datetime.utcnow().isoformat()
    }

# ===============================
# AI AGENT ENDPOINTS
# ===============================

class ChatRequest(BaseModel):
    """Request model for chat with AI agent."""
    message: str
    player_context: Optional[str] = None

class ChatResponse(BaseModel):
    """Response model for chat with AI agent."""
    response: str
    conversation_id: Optional[str] = None

@app.post("/ai/chat", tags=["AI Agent"])
async def chat_with_agent(chat_request: ChatRequest):
    """Chat with the AI agent about player performance."""
    try:
        # Import the agent
        from ..ai_agent.anthropic_agent import get_agent
        
        agent = get_agent()
        response = await agent.chat(
            message=chat_request.message,
            player_context=chat_request.player_context
        )
        
        return ChatResponse(response=response)
        
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI agent error: {str(e)}"
        )

@app.post("/ai/chat/stream", tags=["AI Agent"])
async def chat_with_agent_stream(chat_request: ChatRequest):
    """Chat with the AI agent about player performance with streaming response."""
    try:
        # Import the agent
        from ..ai_agent.anthropic_agent import get_agent
        
        agent = get_agent()
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            async for chunk in agent.chat_stream(
                message=chat_request.message,
                player_context=chat_request.player_context
            ):
                # Format as Server-Sent Events
                data = json.dumps(chunk)
                yield f"data: {data}\n\n"
            
            # Send final event to close connection
            yield f"data: {json.dumps({'type': 'close'})}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in AI chat stream: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI agent error: {str(e)}"
        )

@app.post("/ai/reset", tags=["AI Agent"])
async def reset_conversation():
    """Reset the AI agent conversation."""
    try:
        from ..ai_agent.anthropic_agent import get_agent
        
        agent = get_agent()
        agent.reset_conversation()
        
        return {"message": "Conversation reset successfully"}
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting conversation: {str(e)}"
        )

@app.get("/ai/history", tags=["AI Agent"])
async def get_conversation_history():
    """Get the conversation history with the AI agent."""
    try:
        from ..ai_agent.anthropic_agent import get_agent
        
        agent = get_agent()
        history = agent.get_conversation_history()
        
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting conversation history: {str(e)}"
        )

# ===============================
# ENHANCED UPDATE ENDPOINT
# ===============================

@app.post("/players/{riot_id}/update", tags=["Players"])
async def enhanced_update_player(
    riot_id: str = Path(..., description="Player's Riot ID (username#tag)"),
):
    """Enhanced update player data using anti-detection techniques."""
    try:
        # Import enhanced scraper
        from ..ingest.enhanced_scraper import enhanced_update_player_data
        
        riot_id = validate_riot_id(riot_id)
        
        logger.info(f"Starting enhanced update for {riot_id}")
        
        # Use enhanced scraper
        result = await enhanced_update_player_data(riot_id)
        
        # Check if result has the expected structure
        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid response from enhanced scraper"
            )
        
        # Check for errors in the result
        if result.get("status") == "error":
            return {
                "status": "failed",
                "message": f"Enhanced scraper error for {riot_id}",
                "error_details": result.get("error", "Unknown scraper error"),
                "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
                "update_summary": {
                    "total_endpoints": 0,
                    "successful": 0,
                    "failed": 0
                }
            }
        
        # Get summary with safe defaults
        summary = result.get("summary", {})
        successful_count = summary.get("successful", 0)
        
        if successful_count > 0:
            try:
                # Process the updated data immediately
                from ..ingest.data_loader import TrackerDataLoader
                
                # Save to temporary file for processing
                temp_file = PathLib(f"data/temp_update_{riot_id.replace('#', '_')}.json")
                temp_file.parent.mkdir(exist_ok=True)
                
                # Convert to expected format for data loader
                loader_format = {
                    "riot_id": riot_id,
                    "endpoints": result.get("endpoints", {}),
                    "capture_timestamp": result.get("update_timestamp", datetime.utcnow().isoformat())
                }
                
                with open(temp_file, 'w') as f:
                    json.dump(loader_format, f, indent=2, default=str)
                
                # Load into database
                with get_session() as session:
                    loader = TrackerDataLoader()
                    loader.load_file(session, temp_file)
                
                # Clean up temp file
                temp_file.unlink(missing_ok=True)
                
                return {
                    "status": "success",
                    "message": f"Successfully updated {riot_id}",
                    "update_summary": summary,
                    "anti_detection": result.get("anti_detection", {}),
                    "timestamp": result.get("update_timestamp", datetime.utcnow().isoformat())
                }
            except Exception as load_error:
                logger.error(f"Error loading updated data for {riot_id}: {load_error}")
                return {
                    "status": "partial_success",
                    "message": f"Data fetched but failed to load into database for {riot_id}",
                    "update_summary": summary,
                    "anti_detection": result.get("anti_detection", {}),
                    "error_details": f"Database load error: {str(load_error)}",
                    "timestamp": result.get("update_timestamp", datetime.utcnow().isoformat())
                }
        else:
            return {
                "status": "failed",
                "message": f"Failed to fetch new data for {riot_id}",
                "update_summary": summary,
                "error_details": result.get("error", "No successful endpoints"),
                "timestamp": result.get("update_timestamp", datetime.utcnow().isoformat()),
                "anti_detection": result.get("anti_detection", {})
            }
            
    except Exception as e:
        logger.error(f"Enhanced update error for {riot_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Enhanced update failed: {str(e)}"
        )

# ===============================
# ERROR HANDLERS
# ===============================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ===============================
# STARTUP EVENT
# ===============================

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting Tracker.gg Valorant API")
    logger.info("API Documentation available at /docs")
    logger.info("ReDoc documentation available at /redoc")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 