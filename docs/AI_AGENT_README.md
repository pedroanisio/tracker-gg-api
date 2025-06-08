# 🤖 AI Performance Analyst Integration

An intelligent AI agent powered by Anthropic's Claude that provides personalized Valorant performance insights using Model Context Protocol (MCP) for real-time data access.

## 🌟 Features

### 🧠 **Intelligent Analysis**
- **Comprehensive Player Analysis**: Deep dive into performance metrics across all game modes
- **Performance Trend Analysis**: Identifies patterns and trends over customizable time periods
- **Strategic Recommendations**: Data-driven advice for improvement
- **Contextual Insights**: Understands player context and provides relevant suggestions

### 🔧 **MCP Integration**
- **Real-time Data Access**: Direct connection to your Valorant database through MCP tools
- **Player Search**: Find and analyze any player in your database
- **Performance Metrics**: Access detailed statistics, trends, and comparisons
- **Weapon Analysis**: Insights into loadout performance and weapon proficiency

### 💬 **Interactive Chat Interface**
- **Natural Conversations**: Chat naturally about player performance
- **Context Awareness**: Remembers current player and conversation history
- **Multi-turn Dialogues**: Build on previous questions and insights
- **Formatted Responses**: Clear, structured analysis with bullet points and recommendations

## 🚀 Quick Setup

### 1. **Install Dependencies**
```bash
pip install anthropic>=0.50.0 mcp>=1.0.0 websockets>=12.0 python-dotenv>=1.0.0
```

### 2. **Set Environment Variables**
Create a `.env` file in the project root directory:
```bash
# .env file
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional - Database configuration (if different from defaults)
# DATABASE_URL=postgresql://user:password@localhost:5432/valorant_tracker

# Optional - FlareSolverr configuration
# FLARESOLVERR_URL=http://localhost:8191

# Optional - AI Configuration
# CLAUDE_MODEL=claude-3-5-sonnet-20241022
# MAX_TOKENS=2048
# TEMPERATURE=0.7
```

**Important**: Never commit the `.env` file to version control! Add it to `.gitignore`.

### 3. **Get Anthropic API Key**
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create an account or sign in
3. Generate an API key
4. Copy the key and paste it in your `.env` file (replace `your_anthropic_api_key_here`)

### 4. **Start the Application**
```bash
# Start the FastAPI server
uvicorn src.expose.api:app --host 0.0.0.0 --port 8000 --reload
```

### 5. **Access the Dashboard**
- Open http://localhost:8000/dashboard
- The AI chat interface is integrated into the main dashboard

## 🛠 How It Works

### **MCP Server Architecture**
```
Web UI ↔ FastAPI ↔ Anthropic Claude ↔ MCP Tools ↔ PostgreSQL Database
```

1. **User Input**: Chat messages sent through web interface
2. **Claude Processing**: Anthropic's Claude analyzes the request
3. **Tool Selection**: Claude decides which MCP tools to use
4. **Data Retrieval**: MCP tools query the Valorant database
5. **Analysis**: Claude processes the data and generates insights
6. **Response**: Formatted analysis returned to user

### **Available MCP Tools**

#### 🔍 `search_player`
Search for players by Riot ID or username
```json
{
  "riot_id": "PlayerName#1234"
}
```

#### 📊 `get_player_overview`
Get comprehensive player statistics and recent activity
```json
{
  "riot_id": "PlayerName#1234"
}
```

#### 📈 `analyze_performance_trends`
Analyze performance trends over customizable time periods
```json
{
  "riot_id": "PlayerName#1234",
  "days": 30
}
```

## 💡 Example Conversations

### **Basic Player Analysis**
```
User: "Analyze PlayerName#1234's performance"

AI: I'll analyze PlayerName#1234's performance for you. Let me gather their data...

[Uses MCP tools to fetch player data]

Based on the analysis of PlayerName#1234's recent performance:

**Performance Summary:**
• 45 matches played in the last 30 days
• 1.23 K/D ratio (above average)
• 67% win rate in competitive
• 245 average combat score

**Strengths:**
• Consistent aim with 24% headshot rate
• Strong clutch performance (78% 1v1 win rate)
• Excellent map awareness shown in low death count

**Areas for Improvement:**
• Ability usage could be optimized (low util damage)
• Entry fragging potential underutilized
• Consider expanding agent pool beyond current 2 mains

**Recommendations:**
• Focus on ability combos in aim training
• Practice entry strategies on Ascent and Bind
• Try Initiator agents to complement playstyle
```

### **Trend Analysis**
```
User: "How has their performance changed in the last week?"

AI: Let me compare their recent performance to their longer-term trends...

[Analyzes performance data across different time periods]

**Recent Performance Trends (Last 7 days vs Previous 30 days):**

**Positive Changes:**
• K/D improved from 1.23 to 1.45 (+18%)
• Win rate increased from 67% to 78% (+11%)
• ADR improved by 23 points

**Areas of Concern:**
• Slightly fewer matches played (might indicate tilt)
• Headshot % decreased by 3%

**Analysis:**
The player is clearly on an upward trajectory! The improved K/D and win rate suggest they've recently addressed some fundamental issues. The slight dip in headshot percentage while maintaining higher K/D indicates better positioning and game sense.

**Recommendation:**
Keep the current momentum going. The reduced match count might indicate they're being more selective about when they play, which is actually positive for avoiding tilt.
```

## 🎯 Chat Commands & Tips

### **Effective Questions to Ask**

#### **Performance Analysis**
- "Analyze [player#tag]'s overall performance"
- "What are their strengths and weaknesses?"
- "How do they perform in different game modes?"

#### **Trend Analysis**
- "How has their performance changed recently?"
- "Are they improving or declining?"
- "Compare their last week to last month"

#### **Strategic Insights**
- "What should they focus on to improve?"
- "Which agents suit their playstyle?"
- "What maps do they perform best/worst on?"

#### **Weapon Analysis**
- "How do they perform with different weapons?"
- "What's their best weapon choice?"
- "Should they adjust their loadout?"

### **Tips for Better Conversations**
1. **Be Specific**: Use exact Riot IDs for accurate analysis
2. **Ask Follow-ups**: Build on previous insights for deeper analysis
3. **Context Matters**: Search for a player first to provide context
4. **Use Time Ranges**: Specify periods for trend analysis

## 🔧 Advanced Configuration

### **Environment Variables**
```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional - Database configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Optional - AI Configuration
CLAUDE_MODEL=claude-3-5-sonnet-20241022
MAX_TOKENS=2048
TEMPERATURE=0.7
```

### **API Endpoints**

#### **Chat with AI**
```bash
POST /ai/chat
Content-Type: application/json

{
  "message": "Analyze player performance",
  "player_context": "PlayerName#1234"
}
```

#### **Reset Conversation**
```bash
POST /ai/reset
```

#### **Get Chat History**
```bash
GET /ai/history
```

## 🚨 Troubleshooting

### **Common Issues**

#### **"AI agent error: Authentication failed"** or **"Could not resolve authentication method"**
- **Check .env file**: Ensure you have created a `.env` file in the project root
- **Verify API key**: Check that `ANTHROPIC_API_KEY` is set in your `.env` file
- **Key format**: Ensure there are no extra spaces or quotes around the API key
- **File location**: The `.env` file must be in the project root directory
- **Restart server**: Restart the FastAPI server after modifying the `.env` file
- **API key validity**: Verify the API key is valid and has sufficient credits
- **Environment loading**: Check that `python-dotenv` is installed

**Example .env file:**
```
ANTHROPIC_API_KEY=sk-ant-api03-abcd1234...
```

#### **"Error executing tool: Player not found"**
- Verify the player exists in your database
- Check the Riot ID format (username#tag)
- Ensure data ingestion has been completed

#### **"No data returned from tool"**
- Check database connectivity
- Verify the player has sufficient data for analysis
- Check if the requested time period has data

#### **Chat interface not responding**
- Check browser console for JavaScript errors
- Verify the FastAPI server is running
- Ensure all dependencies are installed

### **Performance Optimization**
- The AI responses are cached to improve speed
- Large time ranges may take longer to analyze
- Consider reducing conversation history for faster responses

## 🔐 Security Considerations

- **API Key Protection**: Never commit API keys to version control
- **Rate Limiting**: Be mindful of Anthropic's API rate limits
- **Data Privacy**: Player data is processed securely through MCP
- **Access Control**: Consider adding authentication for production use

## 🎮 Real-World Usage Examples

### **Coaching Scenarios**
- **Team Analysis**: "Compare all team members' recent performance"
- **Strategy Planning**: "What maps should we avoid based on our stats?"
- **Player Development**: "Which player has improved the most?"

### **Self-Improvement**
- **Regular Check-ins**: "How am I doing this week?"
- **Goal Setting**: "What should I focus on to reach the next rank?"
- **Progress Tracking**: "Am I getting better at my aim?"

### **Community Management**
- **Player Spotlights**: "Who are our most improved players?"
- **Performance Insights**: "What trends do we see across all players?"
- **Coaching Recommendations**: "Which players need coaching support?"

## 🔄 Future Enhancements

### **Planned Features**
- **Multi-player comparisons**: Compare multiple players simultaneously
- **Advanced analytics**: Win rate predictions and rank progression estimates
- **Coach mode**: Specialized prompts for team coaching scenarios
- **Data export**: Export analysis reports as PDF or images
- **Voice interface**: Voice-to-text for hands-free analysis

### **MCP Tool Expansions**
- **Map-specific analysis**: Performance breakdown by map
- **Agent recommendations**: Suggest optimal agent picks
- **Match prediction**: Predict outcomes based on historical data
- **Team synergy analysis**: Understand player compatibility

Enjoy your AI-powered Valorant analysis! 🎯🤖 