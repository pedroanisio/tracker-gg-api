# Valorant Stats Web Dashboard

A modern web interface for viewing comprehensive Valorant player statistics from tracker.gg data.

## Features

🎯 **Comprehensive Player Stats**: View all available statistics for any player
🏆 **Premier Data**: Dedicated section for Premier league statistics  
📊 **All Playlists**: Complete breakdown of stats across different game modes
🔫 **Weapon Loadouts**: Performance statistics for different weapons
📈 **Performance Timeline**: Historical performance data with customizable time ranges
📱 **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
🌙 **Valorant-themed Dark UI**: Beautiful dark theme matching Valorant's aesthetic

## How to Use

### 1. Start the API Server

Make sure your FastAPI server is running:

```bash
# From the project root
python -m src.expose.api
```

Or if using uvicorn directly:

```bash
uvicorn src.expose.api:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Access the Dashboard

Open your web browser and navigate to:
- **Dashboard**: http://localhost:8000/dashboard
- **API Documentation**: http://localhost:8000/docs

### 3. Search for a Player

1. Enter a Riot ID in the format `username#tag` (e.g., `PlayerName#1234`)
2. Click the Search button or press Enter
3. The dashboard will load all available statistics for that player

## Dashboard Sections

### 🔍 Player Information
- Basic player details (Riot ID, username, tag)
- Account activity timestamps
- Data summary with segment counts

### 🏆 Premier Stats
- Premier league specific statistics
- Competitive performance metrics
- Tournament data (if available)

### 📊 All Playlists
- Statistics broken down by game mode
- Competitive, Unrated, Spike Rush, etc.
- Performance comparison across different playlists

### 🔫 Weapon Loadouts
- Performance statistics for different weapons
- Accuracy, damage, and kill statistics per weapon
- Loadout effectiveness analysis

### 📈 Performance Timeline
- Historical performance data over time
- Customizable time ranges (7, 14, 30, 60 days)
- Filter by specific playlists
- Daily performance metrics including:
  - Kills, Deaths, K/D ratio
  - Matches played, Wins, Win rate
  - Average Damage per Round (ADR)

## API Endpoints Used

The dashboard consumes the following API endpoints:
- `/players/{riot_id}` - Basic player information
- `/players/{riot_id}/premier` - Premier statistics
- `/players/{riot_id}/playlists` - All playlist data
- `/players/{riot_id}/loadouts` - Weapon loadout statistics
- `/players/{riot_id}/heatmap` - Performance timeline data

## Technical Details

### Frontend Stack
- **HTML5** with semantic markup
- **Modern CSS** with CSS Grid and Flexbox
- **Vanilla JavaScript** (ES6+) with async/await
- **Font Awesome** icons
- **Responsive design** with mobile-first approach

### Styling
- **Dark theme** inspired by Valorant's visual design
- **CSS custom properties** for consistent theming
- **Smooth animations** and transitions
- **Accessible color contrast** ratios

### JavaScript Features
- **Modular class-based architecture**
- **Parallel API requests** for optimal performance
- **Error handling** with user-friendly messages
- **Real-time data updates** when changing timeline filters
- **Responsive data visualization**

## Troubleshooting

### Player Not Found
- Ensure the Riot ID format is correct (`username#tag`)
- Check that the player exists in your database
- Verify the player has been ingested through your data pipeline

### No Data Displayed
- Some sections may be empty if the player hasn't played those game modes
- Premier data is only available for players who participate in Premier
- Timeline data depends on having heatmap data in your database

### API Connection Issues
- Ensure the FastAPI server is running
- Check that the server is accessible at the expected URL
- Verify CORS settings if accessing from a different domain

## Customization

The dashboard is highly customizable:

### Styling
- Modify `src/expose/static/css/style.css` to change colors, fonts, or layout
- Update CSS custom properties in `:root` to change the theme

### Functionality
- Edit `src/expose/static/js/app.js` to add new features or modify data display
- Add new sections by extending the HTML template and JavaScript class

### Data Display
- Customize which statistics are shown by modifying the `isImportantStat()` method
- Change the number of displayed stats by updating the slice limits
- Add new stat categories or formatting in the extraction methods

## Performance Notes

- The dashboard loads all data in parallel for optimal performance
- Uses `Promise.allSettled()` to handle partial data gracefully
- Implements proper error boundaries to handle missing data sections
- Responsive design ensures good performance on all device types

Enjoy exploring your Valorant statistics! 🎮 