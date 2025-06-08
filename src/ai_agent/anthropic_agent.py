"""
Anthropic AI Agent for Valorant Player Insights.
Uses MCP tools to provide intelligent analysis of player performance.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str

class ValorantAgent:
    """AI agent for providing Valorant player insights."""
    
    def __init__(self):
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable is not set!")
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it in your .env file or environment variables."
            )
        
        self.anthropic = Anthropic(api_key=api_key)
        self.conversation_history = []
        logger.info("ValorantAgent initialized successfully with API key")
        
    async def chat(self, message: str, player_context: Optional[str] = None) -> str:
        """
        Chat with the AI agent about Valorant performance.
        
        Args:
            message: User's message
            player_context: Current player being analyzed (riot_id)
            
        Returns:
            AI agent's response
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt()
            
            # Add player context if provided
            if player_context:
                system_prompt += f"\n\nCurrent player context: {player_context}"
            
            # Prepare messages
            messages = [
                {"role": "user", "content": message}
            ]
            
            # Add conversation history
            if self.conversation_history:
                messages = self.conversation_history + messages
            
            # Make request to Claude
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                temperature=0.7,
                system=system_prompt,
                messages=messages,
                tools=self._get_mcp_tools()
            )
            
            # Process response and tool calls
            response_text = ""
            has_tool_calls = any(content.type == "tool_use" for content in response.content)
            
            for content in response.content:
                if content.type == "text":
                    response_text += content.text
                elif content.type == "tool_use":
                    # Execute MCP tool
                    tool_result = await self._execute_mcp_tool(
                        content.name, 
                        content.input
                    )
                    
                    # Add tool result to context and get follow-up response
                    follow_up_messages = messages + [
                        {"role": "assistant", "content": response.content},
                        {"role": "user", "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": tool_result
                            }
                        ]}
                    ]
                    
                    follow_up = self.anthropic.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=2048,
                        temperature=0.7,
                        system=system_prompt,
                        messages=follow_up_messages
                    )
                    
                    response_text += follow_up.content[0].text if follow_up.content else ""
            
            # Update conversation history (avoid tool call complexity)
            if has_tool_calls:
                # For tool calls, reset conversation history to avoid Claude API issues
                self.conversation_history = []
                if response_text.strip():
                    # Start fresh conversation with this exchange
                    self.conversation_history.append({"role": "user", "content": message})
                    self.conversation_history.append({"role": "assistant", "content": response_text})
            else:
                # Simple text responses can be added normally
                self.conversation_history.append({"role": "user", "content": message})
                if response_text.strip():
                    self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-8:]
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    async def chat_stream(self, message: str, player_context: Optional[str] = None):
        """
        Chat with the AI agent about Valorant performance with streaming response.
        
        Args:
            message: User's message
            player_context: Current player being analyzed (riot_id)
            
        Yields:
            Streaming response chunks
        """
        logger.info(f"🚀 Streaming Chat: Starting stream for message='{message[:50]}...', player_context='{player_context}'")
        try:
            # Build system prompt
            logger.debug(f"🚀 Streaming Chat: Building system prompt")
            system_prompt = self._build_system_prompt()
            
            # Add player context if provided
            if player_context:
                logger.debug(f"🚀 Streaming Chat: Adding player context: {player_context}")
                system_prompt += f"\n\nCurrent player context: {player_context}"
            
            # Prepare messages
            logger.debug(f"🚀 Streaming Chat: Preparing messages")
            messages = [
                {"role": "user", "content": message}
            ]
            
            # Add conversation history
            if self.conversation_history:
                logger.debug(f"🚀 Streaming Chat: Adding conversation history ({len(self.conversation_history)} messages)")
                messages = self.conversation_history + messages
            
            # Make streaming request to Claude
            response_text = ""
            
            # Use regular message creation for now (streaming has async context issues)
            logger.info(f"🚀 Streaming Chat: Making initial API call to Claude with {len(messages)} messages")
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                temperature=0.7,
                system=system_prompt,
                messages=messages,
                tools=self._get_mcp_tools()
            )
            logger.info(f"🚀 Streaming Chat: Initial Claude response received with {len(response.content)} content items")
            
            # Simulate streaming by yielding chunks of the response
            response_text = ""
            has_tool_calls = any(content.type == "tool_use" for content in response.content)
            
            # Handle tool calls first
            for content in response.content:
                if content.type == "tool_use":
                    logger.info(f"🔄 Streaming: Tool use detected - {content.name} with input: {content.input}")
                    yield {"type": "tool_call", "content": f"Using tool: {content.name}"}
                    
                    logger.info(f"🔄 Streaming: Starting tool execution for {content.name}")
                    tool_result = await self._execute_mcp_tool(
                        content.name, 
                        content.input
                    )
                    logger.info(f"🔄 Streaming: Tool execution completed for {content.name}, result length: {len(tool_result)}")
                    
                    # Get follow-up response with tool result
                    logger.info(f"🔄 Streaming: Preparing follow-up message with tool result")
                    follow_up_messages = messages + [
                        {"role": "assistant", "content": response.content},
                        {"role": "user", "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": tool_result
                            }
                        ]}
                    ]
                    
                    logger.info(f"🔄 Streaming: Making follow-up API call to Claude")
                    follow_up_response = self.anthropic.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=2048,
                        temperature=0.7,
                        system=system_prompt,
                        messages=follow_up_messages
                    )
                    logger.info(f"🔄 Streaming: Follow-up response received from Claude")
                    
                    # Stream the follow-up text response
                    logger.info(f"🔄 Streaming: Processing follow-up response content ({len(follow_up_response.content)} items)")
                    for follow_content in follow_up_response.content:
                        if follow_content.type == "text":
                            text = follow_content.text
                            response_text += text
                            logger.debug(f"🔄 Streaming: Streaming follow-up text ({len(text)} chars)")
                            
                            # Yield in chunks for streaming effect
                            words = text.split(' ')
                            for i, word in enumerate(words):
                                if i > 0:
                                    yield {"type": "text", "content": " "}
                                yield {"type": "text", "content": word}
                                # Add small delay for streaming effect (optional)
                                await asyncio.sleep(0.03)
                        else:
                            logger.warning(f"🔄 Streaming: Unexpected content type in follow-up: {follow_content.type}")
                    
                elif content.type == "text":
                    text = content.text
                    response_text += text
                    
                    # Yield in chunks for streaming effect
                    words = text.split(' ')
                    for i, word in enumerate(words):
                        if i > 0:
                            yield {"type": "text", "content": " "}
                        yield {"type": "text", "content": word}
                        # Add small delay for streaming effect
                        await asyncio.sleep(0.03)
            
            # Update conversation history (avoid tool call complexity)
            logger.debug(f"🚀 Streaming Chat: Updating conversation history")
            
            if has_tool_calls:
                # For tool calls, reset conversation history to avoid Claude API issues
                logger.debug(f"🚀 Streaming Chat: Tool calls detected, resetting conversation history")
                self.conversation_history = []
                if response_text.strip():
                    # Start fresh conversation with this exchange
                    self.conversation_history.append({"role": "user", "content": message})
                    self.conversation_history.append({"role": "assistant", "content": response_text})
            else:
                # Simple text responses can be added normally
                self.conversation_history.append({"role": "user", "content": message})
                if response_text.strip():
                    self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-8:]
                
            logger.info(f"🚀 Streaming Chat: Streaming completed successfully")
            yield {"type": "done"}
            
        except Exception as e:
            logger.error(f"🚀 Streaming Chat: Error in chat stream: {e}", exc_info=True)
            yield {"type": "error", "content": f"I apologize, but I encountered an error while processing your request: {str(e)}"}
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI agent."""
        return """
You are a professional Valorant performance analyst and coach. You have access to detailed player statistics and performance data through specialized tools. Your role is to:

1. **Analyze Player Performance**: Use the available tools to gather comprehensive data about players, including their statistics across different game modes, performance trends, and weapon proficiency.

2. **Provide Strategic Insights**: Offer actionable advice based on the data, including:
   - Strengths and weaknesses analysis
   - Performance trends and patterns
   - Specific areas for improvement
   - Strategic recommendations for different game modes

3. **Be Data-Driven**: Always base your analysis on actual statistics rather than assumptions. Use the MCP tools to gather current and historical data before making recommendations.

4. **Communicate Clearly**: Explain complex statistics in an understandable way. Use comparisons, percentages, and clear metrics to illustrate points.

5. **Stay Focused on Valorant**: Your expertise is specifically in Valorant gameplay, strategies, and performance optimization.

Available tools allow you to:
- Search for players and get their basic information
- Analyze comprehensive player statistics and performance data
- Examine performance trends over time
- Compare different time periods
- Analyze weapon/loadout performance

When a user asks about a player, always start by gathering their data using the available tools. Be proactive in using multiple tools to build a complete picture before providing analysis.

Remember to be encouraging and constructive in your feedback, focusing on growth and improvement opportunities.
"""

    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tools definition for Claude."""
        return [
            {
                "name": "search_player",
                "description": "Search for a player by riot ID or username",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "riot_id": {
                            "type": "string",
                            "description": "Full Riot ID (username#tag) or just username to search"
                        }
                    },
                    "required": ["riot_id"]
                }
            },
            {
                "name": "get_player_overview",
                "description": "Get comprehensive overview of player statistics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "riot_id": {
                            "type": "string",
                            "description": "Player's Riot ID (username#tag)"
                        }
                    },
                    "required": ["riot_id"]
                }
            },
            {
                "name": "analyze_performance_trends",
                "description": "Analyze player's performance trends over time",
                "input_schema": {
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
            }
        ]

    async def _execute_mcp_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute an MCP tool and return the result.
        This is a simplified version - in a full implementation, 
        this would connect to the actual MCP server.
        """
        logger.info(f"🤖 AI Agent: Starting MCP tool execution - tool_name='{tool_name}', tool_input={tool_input}")
        try:
            # Import the MCP server functions
            logger.debug(f"🤖 AI Agent: Importing ValorantMCPServer")
            from .mcp_server import ValorantMCPServer
            
            logger.debug(f"🤖 AI Agent: Creating MCP server instance")
            server = ValorantMCPServer()
            
            logger.info(f"🤖 AI Agent: Executing tool '{tool_name}'")
            
            if tool_name == "search_player":
                logger.debug(f"🤖 AI Agent: Calling search_player with riot_id='{tool_input['riot_id']}'")
                result = await server.search_player(tool_input["riot_id"])
            elif tool_name == "get_player_overview":
                logger.debug(f"🤖 AI Agent: Calling get_player_overview with riot_id='{tool_input['riot_id']}'")
                result = await server.get_player_overview(tool_input["riot_id"])
            elif tool_name == "analyze_performance_trends":
                logger.debug(f"🤖 AI Agent: Calling analyze_performance_trends with riot_id='{tool_input['riot_id']}', days={tool_input.get('days', 30)}")
                result = await server.analyze_performance_trends(
                    tool_input["riot_id"],
                    tool_input.get("days", 30)
                )
            else:
                logger.error(f"🤖 AI Agent: Unknown tool requested: {tool_name}")
                return f"Unknown tool: {tool_name}"
            
            logger.debug(f"🤖 AI Agent: Tool '{tool_name}' completed, processing result")
            
            # Extract text content from result
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                logger.info(f"🤖 AI Agent: Tool '{tool_name}' returned {len(response_text)} characters")
                return response_text
            else:
                logger.warning(f"🤖 AI Agent: Tool '{tool_name}' returned no content")
                return "No data returned from tool"
                
        except Exception as e:
            logger.error(f"🤖 AI Agent: Error executing MCP tool {tool_name}: {e}", exc_info=True)
            return f"Error executing tool: {str(e)}"

    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []

    def get_conversation_history(self) -> List[ChatMessage]:
        """Get the conversation history."""
        return [ChatMessage(role=msg["role"], content=msg["content"]) 
                for msg in self.conversation_history]

# Global agent instance
_agent_instance = None

def get_agent() -> ValorantAgent:
    """Get the global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ValorantAgent()
    return _agent_instance 