"""
MCP Server for Valorant Player Data Access.
Provides tools for AI agent to access and analyze player statistics.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR
)
from sqlmodel import Session, select, and_, desc
from sqlalchemy import func

# Import database models
from ..shared.database import (
    get_session, Player, PlayerSegment, StatisticValue,
    HeatmapData, PartyStatistic, engine
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValorantMCPServer:
    """MCP Server for Valorant data access."""
    
    def __init__(self):
        self.server = Server("valorant-stats")
        self.setup_tools()
    
    def setup_tools(self):
        """Set up all available tools for the MCP server."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="search_player",
                        description="Search for a player by riot ID or username",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "riot_id": {
                                    "type": "string",
                                    "description": "Full Riot ID (username#tag) or just username to search"
                                }
                            },
                            "required": ["riot_id"]
                        }
                    ),
                    Tool(
                        name="get_player_overview",
                        description="Get comprehensive overview of player statistics",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "riot_id": {
                                    "type": "string",
                                    "description": "Player's Riot ID (username#tag)"
                                }
                            },
                            "required": ["riot_id"]
                        }
                    ),
                    Tool(
                        name="analyze_performance_trends",
                        description="Analyze player's performance trends over time",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "riot_id": {
                                    "type": "string",
                                    "description": "Player's Riot ID (username#tag)"
                                },
                                "days": {
                                    "type": "integer",
                                    "description": "Number of days to analyze (default: 30)",
                                    "default": 30
                                }
                            },
                            "required": ["riot_id"]
                        }
                    )
                ]
            )

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls."""
            logger.info(f"🛠️ MCP: Tool call received - name='{name}', arguments={arguments}")
            try:
                if name == "search_player":
                    logger.info(f"🛠️ MCP: Calling search_player")
                    result = await self.search_player(arguments["riot_id"])
                    logger.info(f"🛠️ MCP: search_player completed successfully")
                    return result
                elif name == "get_player_overview":
                    logger.info(f"🛠️ MCP: Calling get_player_overview")
                    result = await self.get_player_overview(arguments["riot_id"])
                    logger.info(f"🛠️ MCP: get_player_overview completed successfully")
                    return result
                elif name == "analyze_performance_trends":
                    logger.info(f"🛠️ MCP: Calling analyze_performance_trends")
                    result = await self.analyze_performance_trends(
                        arguments["riot_id"],
                        arguments.get("days", 30)
                    )
                    logger.info(f"🛠️ MCP: analyze_performance_trends completed successfully")
                    return result
                else:
                    logger.error(f"🛠️ MCP: Unknown tool requested: {name}")
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                        isError=True
                    )
            except Exception as e:
                logger.error(f"🛠️ MCP: Error in tool {name}: {e}", exc_info=True)
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )

    async def search_player(self, riot_id: str) -> CallToolResult:
        """Search for a player by riot ID or username."""
        logger.info(f"🔍 MCP: search_player called with riot_id='{riot_id}'")
        try:
            logger.debug(f"🔍 MCP: Creating database session for search_player")
            with Session(engine) as session:
                # Try exact match first
                stmt = select(Player).where(Player.riot_id == riot_id)
                player = session.exec(stmt).first()
                
                if not player:
                    # Try username search
                    username = riot_id.split('#')[0] if '#' in riot_id else riot_id
                    stmt = select(Player).where(Player.username.ilike(f"%{username}%"))
                    players = session.exec(stmt).all()
                    
                    if not players:
                        return CallToolResult(
                            content=[TextContent(type="text", text="No players found matching the search criteria.")]
                        )
                    
                    # Return multiple matches
                    results = []
                    for p in players[:10]:  # Limit to 10 results
                        results.append({
                            "riot_id": p.riot_id,
                            "username": p.username,
                            "tag": p.tag,
                            "last_updated": p.last_updated.isoformat()
                        })
                    
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"Found {len(results)} players:\n" + 
                                 json.dumps(results, indent=2)
                        )]
                    )
                
                # Single exact match
                result = {
                    "riot_id": player.riot_id,
                    "username": player.username,
                    "tag": player.tag,
                    "first_seen": player.first_seen.isoformat(),
                    "last_updated": player.last_updated.isoformat()
                }
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Player found:\n{json.dumps(result, indent=2)}"
                    )]
                )
                
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error searching player: {str(e)}")],
                isError=True
            )

    async def get_player_overview(self, riot_id: str) -> CallToolResult:
        """Get comprehensive overview of player statistics."""
        logger.info(f"📊 MCP: get_player_overview called with riot_id='{riot_id}'")
        try:
            logger.debug(f"📊 MCP: Creating database session for player overview")
            with Session(engine) as session:
                # Get player
                stmt = select(Player).where(Player.riot_id == riot_id)
                player = session.exec(stmt).first()
                
                if not player:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Player not found.")]
                    )
                
                # Get all segments
                segments_stmt = select(PlayerSegment).where(PlayerSegment.player_id == player.id)
                segments = session.exec(segments_stmt).all()
                
                # Get recent heatmap data
                heatmap_stmt = select(HeatmapData).where(
                    HeatmapData.player_id == player.id
                ).order_by(desc(HeatmapData.date)).limit(7)
                recent_heatmap = session.exec(heatmap_stmt).all()
                
                overview = {
                    "player_info": {
                        "riot_id": player.riot_id,
                        "username": player.username,
                        "tag": player.tag,
                        "first_seen": player.first_seen.isoformat(),
                        "last_updated": player.last_updated.isoformat()
                    },
                    "data_summary": {
                        "total_segments": len(segments),
                        "recent_activity_days": len(recent_heatmap)
                    },
                    "recent_performance": []
                }
                
                # Add recent performance summary
                for entry in recent_heatmap:
                    overview["recent_performance"].append({
                        "date": entry.date.isoformat(),
                        "playlist": entry.playlist,
                        "matches": entry.matches,
                        "kd_ratio": entry.kd_ratio,
                        "win_pct": entry.win_pct,
                        "adr": entry.adr
                    })
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Player Overview:\n{json.dumps(overview, indent=2)}"
                    )]
                )
                
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting player overview: {str(e)}")],
                isError=True
            )

    async def analyze_performance_trends(self, riot_id: str, days: int = 30) -> CallToolResult:
        """Analyze player's performance trends over time."""
        logger.info(f"📈 MCP: analyze_performance_trends called with riot_id='{riot_id}', days={days}")
        try:
            logger.debug(f"📈 MCP: Creating database session for performance trends")
            with Session(engine) as session:
                # Get player
                stmt = select(Player).where(Player.riot_id == riot_id)
                player = session.exec(stmt).first()
                
                if not player:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Player not found.")]
                    )
                
                # Get heatmap data for specified period
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                heatmap_stmt = select(HeatmapData).where(
                    and_(
                        HeatmapData.player_id == player.id,
                        HeatmapData.date >= start_date,
                        HeatmapData.date <= end_date
                    )
                ).order_by(HeatmapData.date)
                
                heatmap_data = session.exec(heatmap_stmt).all()
                
                if not heatmap_data:
                    return CallToolResult(
                        content=[TextContent(type="text", text="No performance data found for the specified period.")]
                    )
                
                # Calculate trends
                trends = self._calculate_trends(heatmap_data)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Performance Trends Analysis:\n{json.dumps(trends, indent=2)}"
                    )]
                )
                
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error analyzing trends: {str(e)}")],
                isError=True
            )

    def _calculate_trends(self, heatmap_data: List) -> Dict[str, Any]:
        """Calculate performance trends from heatmap data."""
        if not heatmap_data:
            return {}
        
        # Calculate averages
        total_matches = sum(entry.matches for entry in heatmap_data)
        total_kills = sum(entry.kills for entry in heatmap_data)
        total_deaths = sum(entry.deaths for entry in heatmap_data)
        total_wins = sum(entry.wins for entry in heatmap_data)
        
        avg_kd = total_kills / max(total_deaths, 1)
        avg_win_rate = (total_wins / max(total_matches, 1)) * 100
        avg_adr = sum(entry.adr for entry in heatmap_data) / len(heatmap_data)
        
        return {
            "period_summary": {
                "total_matches": total_matches,
                "total_kills": total_kills,
                "total_deaths": total_deaths,
                "avg_kd_ratio": round(avg_kd, 2),
                "avg_win_rate": round(avg_win_rate, 1),
                "avg_adr": round(avg_adr, 1)
            },
            "activity": {
                "days_with_matches": len(heatmap_data),
                "avg_matches_per_day": round(total_matches / len(heatmap_data), 1)
            }
        }

async def run_mcp_server():
    """Run the MCP server."""
    server = ValorantMCPServer()
    
    # Setup stdio transport
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="valorant-stats",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(run_mcp_server()) 