class ValorantStatsApp {
    constructor() {
        this.currentPlayer = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupEnterKeySearch();
        this.setupChatInterface();
        this.addWelcomeMessage();
    }

    bindEvents() {
        const searchBtn = document.getElementById('searchBtn');
        const timelineDays = document.getElementById('timelineDays');
        const timelinePlaylist = document.getElementById('timelinePlaylist');
        const sendChatBtn = document.getElementById('sendChatBtn');
        const resetChatBtn = document.getElementById('resetChatBtn');

        searchBtn.addEventListener('click', () => this.searchPlayer());
        timelineDays.addEventListener('change', () => this.updateTimeline());
        timelinePlaylist.addEventListener('change', () => this.updateTimeline());
        sendChatBtn.addEventListener('click', () => this.sendChatMessage());
        resetChatBtn.addEventListener('click', () => this.resetChat());
    }

    setupEnterKeySearch() {
        const riotIdInput = document.getElementById('riotId');
        riotIdInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchPlayer();
            }
        });
    }

    async searchPlayer() {
        const riotId = document.getElementById('riotId').value.trim();
        
        if (!riotId) {
            this.showError('Please enter a Riot ID');
            return;
        }

        if (!riotId.includes('#')) {
            this.showError('Invalid Riot ID format. Please use: username#tag');
            return;
        }

        this.showLoading();
        this.hideError();
        this.hidePlayerData();

        try {
            // Fetch all player data in parallel
            const [playerInfo, premierData, playlistsData, loadoutsData] = await Promise.allSettled([
                this.fetchPlayerInfo(riotId),
                this.fetchPremierData(riotId),
                this.fetchPlaylistsData(riotId),
                this.fetchLoadoutsData(riotId)
            ]);

            this.currentPlayer = riotId;
            
            // Display the data
            if (playerInfo.status === 'fulfilled') {
                this.displayPlayerInfo(playerInfo.value);
            }

            if (premierData.status === 'fulfilled') {
                this.displayPremierData(premierData.value);
            } else {
                this.displayNoPremierData();
            }

            if (playlistsData.status === 'fulfilled') {
                this.displayPlaylistsData(playlistsData.value);
                this.populateTimelinePlaylistOptions(playlistsData.value);
            } else {
                this.displayNoPlaylistsData();
            }

            if (loadoutsData.status === 'fulfilled') {
                this.displayLoadoutsData(loadoutsData.value);
            } else {
                this.displayNoLoadoutsData();
            }

            // Load timeline data
            await this.updateTimeline();

            this.hideLoading();
            this.showPlayerData();

        } catch (error) {
            this.hideLoading();
            this.showError(`Error loading player data: ${error.message}`);
        }
    }

    async fetchPlayerInfo(riotId) {
        const response = await fetch(`/players/${encodeURIComponent(riotId)}`);
        if (!response.ok) {
            throw new Error(`Player not found: ${response.status}`);
        }
        return await response.json();
    }

    async fetchPremierData(riotId) {
        const response = await fetch(`/players/${encodeURIComponent(riotId)}/premier`);
        if (!response.ok) {
            throw new Error(`Premier data not found: ${response.status}`);
        }
        return await response.json();
    }

    async fetchPlaylistsData(riotId) {
        const response = await fetch(`/players/${encodeURIComponent(riotId)}/playlists`);
        if (!response.ok) {
            throw new Error(`Playlists data not found: ${response.status}`);
        }
        return await response.json();
    }

    async fetchLoadoutsData(riotId) {
        const response = await fetch(`/players/${encodeURIComponent(riotId)}/loadouts`);
        if (!response.ok) {
            throw new Error(`Loadouts data not found: ${response.status}`);
        }
        return await response.json();
    }

    async fetchTimelineData(riotId, days, playlist = '') {
        let url = `/players/${encodeURIComponent(riotId)}/heatmap?days=${days}`;
        if (playlist) {
            url += `&playlist=${encodeURIComponent(playlist)}`;
        }
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Timeline data not found: ${response.status}`);
        }
        return await response.json();
    }

    displayPlayerInfo(data) {
        const container = document.getElementById('playerBasicInfo');
        
        const basicInfo = [
            { label: 'Riot ID', value: data.riot_id },
            { label: 'Username', value: data.username },
            { label: 'Tag', value: data.tag },
            { label: 'First Seen', value: this.formatDate(data.first_seen) },
            { label: 'Last Updated', value: this.formatDate(data.last_updated) },
            { label: 'Total Segments', value: data.data_summary.total_segments },
            { label: 'Playlist Segments', value: data.data_summary.playlist_segments },
            { label: 'Loadout Segments', value: data.data_summary.loadout_segments }
        ];

        container.innerHTML = basicInfo.map(item => `
            <div class="info-item">
                <div class="label">${item.label}</div>
                <div class="value">${item.value}</div>
            </div>
        `).join('');
    }

    displayPremierData(data) {
        const container = document.getElementById('premierData');
        
        if (!data || Object.keys(data).length === 0) {
            container.innerHTML = '<p>No Premier data available</p>';
            return;
        }

        // Extract stats from the premier data structure
        const stats = this.extractStatsFromPremierData(data);
        
        container.innerHTML = stats.map(stat => `
            <div class="stat-item">
                <div class="stat-value">${stat.value}</div>
                <div class="stat-label">${stat.label}</div>
            </div>
        `).join('');
    }

    displayNoPremierData() {
        const container = document.getElementById('premierData');
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No Premier data available for this player</p>';
    }

    displayPlaylistsData(data) {
        const container = document.getElementById('playlistsData');
        
        if (!data.playlists || Object.keys(data.playlists).length === 0) {
            container.innerHTML = '<p>No playlist data available</p>';
            return;
        }

        const playlistsHtml = Object.entries(data.playlists).map(([playlistName, playlistData]) => {
            const stats = this.extractStatsFromPlaylistData(playlistData);
            
            return `
                <div class="playlist-item">
                    <div class="playlist-header">${this.capitalizePlaylistName(playlistName)}</div>
                    <div class="playlist-stats">
                        ${stats.map(stat => `
                            <div class="playlist-stat">
                                <div class="value">${stat.value}</div>
                                <div class="label">${stat.label}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = playlistsHtml;
    }

    displayNoPlaylistsData() {
        const container = document.getElementById('playlistsData');
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No playlist data available for this player</p>';
    }

    displayLoadoutsData(data) {
        const container = document.getElementById('loadoutsData');
        
        if (!data.loadouts || Object.keys(data.loadouts).length === 0) {
            container.innerHTML = '<p>No loadout data available</p>';
            return;
        }

        const loadoutsHtml = Object.entries(data.loadouts).map(([loadoutKey, loadoutData]) => {
            const stats = this.extractStatsFromLoadoutData(loadoutData);
            
            return `
                <div class="loadout-item">
                    <div class="loadout-header">${loadoutData.display_name || loadoutKey}</div>
                    <div class="loadout-stats">
                        ${stats.map(stat => `
                            <div class="loadout-stat">
                                <div class="label">${stat.label}</div>
                                <div class="value">${stat.value}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = loadoutsHtml;
    }

    displayNoLoadoutsData() {
        const container = document.getElementById('loadoutsData');
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No loadout data available for this player</p>';
    }

    async updateTimeline() {
        if (!this.currentPlayer) return;

        const days = document.getElementById('timelineDays').value;
        const playlist = document.getElementById('timelinePlaylist').value;

        try {
            const timelineData = await this.fetchTimelineData(this.currentPlayer, days, playlist);
            this.displayTimelineData(timelineData);
        } catch (error) {
            this.displayNoTimelineData();
        }
    }

    displayTimelineData(data) {
        const container = document.getElementById('timelineData');
        
        if (!data.data || data.data.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No timeline data available</p>';
            return;
        }

        const timelineHtml = data.data.map(day => `
            <div class="timeline-day">
                <div class="timeline-date">${this.formatDate(day.date)} - ${day.playlist}</div>
                <div class="timeline-stats">
                    <div class="timeline-stat">
                        <div class="value">${day.stats.kills || 0}</div>
                        <div class="label">Kills</div>
                    </div>
                    <div class="timeline-stat">
                        <div class="value">${day.stats.deaths || 0}</div>
                        <div class="label">Deaths</div>
                    </div>
                    <div class="timeline-stat">
                        <div class="value">${(day.stats.kd_ratio || 0).toFixed(2)}</div>
                        <div class="label">K/D</div>
                    </div>
                    <div class="timeline-stat">
                        <div class="value">${day.stats.matches || 0}</div>
                        <div class="label">Matches</div>
                    </div>
                    <div class="timeline-stat">
                        <div class="value">${day.stats.wins || 0}</div>
                        <div class="label">Wins</div>
                    </div>
                    <div class="timeline-stat">
                        <div class="value">${(day.stats.win_pct || 0).toFixed(1)}%</div>
                        <div class="label">Win Rate</div>
                    </div>
                    <div class="timeline-stat">
                        <div class="value">${(day.stats.adr || 0).toFixed(1)}</div>
                        <div class="label">ADR</div>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = timelineHtml;
    }

    displayNoTimelineData() {
        const container = document.getElementById('timelineData');
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No timeline data available for the selected period</p>';
    }

    populateTimelinePlaylistOptions(data) {
        const select = document.getElementById('timelinePlaylist');
        const currentValue = select.value;
        
        // Keep the "All Playlists" option
        select.innerHTML = '<option value="">All Playlists</option>';
        
        if (data.playlists) {
            Object.keys(data.playlists).forEach(playlist => {
                const option = document.createElement('option');
                option.value = playlist;
                option.textContent = this.capitalizePlaylistName(playlist);
                select.appendChild(option);
            });
        }
        
        // Restore previous selection if it still exists
        if (currentValue && [...select.options].some(opt => opt.value === currentValue)) {
            select.value = currentValue;
        }
    }

    extractStatsFromPremierData(data) {
        // Extract meaningful stats from premier data structure
        const stats = [];
        
        if (data.stats) {
            Object.entries(data.stats).forEach(([key, stat]) => {
                stats.push({
                    label: stat.display_name || this.formatStatName(key),
                    value: stat.display_value || stat.value || '0'
                });
            });
        }
        
        return stats.slice(0, 12); // Limit to 12 most important stats
    }

    extractStatsFromPlaylistData(data) {
        const stats = [];
        
        if (data.stats) {
            Object.entries(data.stats).forEach(([key, stat]) => {
                if (this.isImportantStat(key)) {
                    stats.push({
                        label: stat.display_name || this.formatStatName(key),
                        value: stat.display_value || stat.value || '0'
                    });
                }
            });
        }
        
        return stats.slice(0, 8); // Limit to 8 most important stats
    }

    extractStatsFromLoadoutData(data) {
        const stats = [];
        
        if (data.stats) {
            Object.entries(data.stats).forEach(([key, stat]) => {
                stats.push({
                    label: stat.display_name || this.formatStatName(key),
                    value: stat.display_value || stat.value || '0'
                });
            });
        }
        
        return stats;
    }

    isImportantStat(statKey) {
        const importantStats = [
            'kills', 'deaths', 'kd', 'kdr', 'kda', 'matches', 'wins', 'losses',
            'winpct', 'rounds', 'score', 'adr', 'headshots', 'accuracy',
            'damage', 'assists', 'mvps', 'aces', 'clutches'
        ];
        
        return importantStats.some(important => 
            statKey.toLowerCase().includes(important.toLowerCase())
        );
    }

    formatStatName(key) {
        return key.replace(/([A-Z])/g, ' $1')
                 .replace(/^./, str => str.toUpperCase())
                 .trim();
    }

    capitalizePlaylistName(name) {
        return name.split('_')
                  .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ');
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    showLoading() {
        document.getElementById('loading').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
    }

    showError(message) {
        const errorDiv = document.getElementById('error');
        const errorMessage = document.getElementById('errorMessage');
        errorMessage.textContent = message;
        errorDiv.classList.remove('hidden');
    }

    hideError() {
        document.getElementById('error').classList.add('hidden');
    }

    showPlayerData() {
        document.getElementById('playerData').classList.remove('hidden');
    }

    hidePlayerData() {
        document.getElementById('playerData').classList.add('hidden');
    }

    // ===============================
    // CHAT FUNCTIONALITY
    // ===============================

    setupChatInterface() {
        const chatInput = document.getElementById('chatInput');
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendChatMessage();
            }
        });
    }

    addWelcomeMessage() {
        const welcomeMessage = `
            Welcome! I'm your AI Valorant performance analyst. I can help you understand player statistics, identify improvement areas, and provide strategic insights.
            
            Try asking me:
            • "Analyze [player#tag]'s performance"
            • "What are the strengths and weaknesses of this player?"
            • "How has their performance changed recently?"
            • "What should they focus on to improve?"
            
            Search for a player first, then I'll have more context for detailed analysis!
        `;
        
        this.addChatMessage('assistant', welcomeMessage);
    }

    async sendChatMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message) return;
        
        // Clear input and add user message
        chatInput.value = '';
        this.addChatMessage('user', message);
        
        // Disable input while processing
        this.setChatInputState(false);
        
        try {
            // Use streaming endpoint
            await this.streamChatResponse(message);
            
        } catch (error) {
            console.error('Chat error:', error);
            this.addChatMessage('system', `Error: ${error.message}. Please check your connection and try again.`);
        } finally {
            // Re-enable input
            this.setChatInputState(true);
        }
    }

    async streamChatResponse(message) {
        let assistantMessageDiv = null;
        let currentContent = '';
        
        // Create assistant message div for streaming
        assistantMessageDiv = this.addChatMessage('assistant', '');
        
        // Add typing indicator
        const typingIndicator = document.createElement('span');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = '<i class="fas fa-circle"></i>';
        assistantMessageDiv.appendChild(typingIndicator);
        
        try {
            const response = await fetch('/ai/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    player_context: this.currentPlayer
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'text') {
                                // Remove typing indicator if it exists
                                if (typingIndicator && typingIndicator.parentNode) {
                                    typingIndicator.remove();
                                }
                                
                                // Append text content
                                currentContent += data.content;
                                assistantMessageDiv.innerHTML = this.formatMessageContent(currentContent);
                                
                                // Scroll to bottom
                                this.scrollChatToBottom();
                                
                            } else if (data.type === 'tool_call') {
                                // Show tool usage indicator
                                const toolIndicator = document.createElement('div');
                                toolIndicator.className = 'tool-indicator';
                                toolIndicator.innerHTML = `<i class="fas fa-cog fa-spin"></i> ${data.content}`;
                                assistantMessageDiv.appendChild(toolIndicator);
                                
                            } else if (data.type === 'error') {
                                // Handle error
                                currentContent = `Error: ${data.content}`;
                                assistantMessageDiv.innerHTML = this.formatMessageContent(currentContent);
                                assistantMessageDiv.classList.add('error-message');
                                
                            } else if (data.type === 'done' || data.type === 'close') {
                                // Remove any remaining indicators
                                if (typingIndicator && typingIndicator.parentNode) {
                                    typingIndicator.remove();
                                }
                                const toolIndicators = assistantMessageDiv.querySelectorAll('.tool-indicator');
                                toolIndicators.forEach(indicator => indicator.remove());
                                
                                // Mark message as complete (removes blinking cursor)
                                assistantMessageDiv.classList.add('complete');
                                break;
                            }
                            
                        } catch (parseError) {
                            console.warn('Failed to parse SSE data:', line);
                        }
                    }
                }
            }
            
        } catch (error) {
            // Remove typing indicator
            if (typingIndicator && typingIndicator.parentNode) {
                typingIndicator.remove();
            }
            
            // Show error in message
            assistantMessageDiv.innerHTML = this.formatMessageContent(`Error: ${error.message}`);
            assistantMessageDiv.classList.add('error-message');
            assistantMessageDiv.classList.add('complete');
            throw error;
        }
    }

    formatMessageContent(content) {
        // Convert line breaks to HTML and preserve formatting
        return content.replace(/\n/g, '<br>');
    }

    scrollChatToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async resetChat() {
        try {
            await fetch('/ai/reset', { method: 'POST' });
            
            // Clear chat messages
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = '';
            
            // Add welcome message back
            this.addWelcomeMessage();
            
        } catch (error) {
            console.error('Reset chat error:', error);
            this.addChatMessage('system', 'Error resetting conversation. Please refresh the page.');
        }
    }

    addChatMessage(role, content) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        
        // Format the content (convert line breaks to HTML)
        const formattedContent = content.replace(/\n/g, '<br>');
        messageDiv.innerHTML = formattedContent;
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }

    addChatLoading() {
        const chatMessages = document.getElementById('chatMessages');
        const loadingDiv = document.createElement('div');
        const loadingId = 'loading-' + Date.now();
        
        loadingDiv.id = loadingId;
        loadingDiv.className = 'chat-loading';
        loadingDiv.innerHTML = `
            AI is thinking...
            <div class="dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;
        
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return loadingId;
    }

    removeChatLoading(loadingId) {
        const loadingDiv = document.getElementById(loadingId);
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }

    setChatInputState(enabled) {
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendChatBtn');
        
        chatInput.disabled = !enabled;
        sendBtn.disabled = !enabled;
        
        if (enabled) {
            chatInput.focus();
        }
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ValorantStatsApp();
}); 