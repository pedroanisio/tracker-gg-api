"""
User Management System for Tracker.gg Data Ingestion

This module handles:
- Configuration of which users to track
- Automatic initialization of all user data at startup
- Separation between initialization and updates
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..shared.utils import get_logger

logger = get_logger(__name__)


class UserManager:
    """Manages tracked users and their data initialization/updates."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize UserManager.
        
        Args:
            config_file: Path to users configuration file (defaults to users.json)
        """
        self.config_file = config_file or "users.json"
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_path = self.base_dir / self.config_file
        self._tracked_users: Optional[Set[str]] = None
        
    def get_tracked_users(self) -> List[str]:
        """
        Get list of riot_ids to track.
        
        Priority order:
        1. TRACKED_USERS environment variable (comma-separated)
        2. users.json configuration file
        3. Default list if neither exists
        
        Returns:
            List of riot_ids in format "username#tag"
        """
        # Check environment variable first
        env_users = os.getenv("TRACKED_USERS")
        if env_users:
            users = [user.strip() for user in env_users.split(",") if user.strip()]
            logger.info(f"Loaded {len(users)} users from TRACKED_USERS environment variable")
            return users
        
        # Check configuration file
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    users = config.get("tracked_users", [])
                    if users:
                        logger.info(f"Loaded {len(users)} users from {self.config_file}")
                        return users
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
        
        # Default fallback list
        default_users = [
            "appoloZ#sun",  # Default user from the system
        ]
        
        logger.warning(f"No user configuration found, using default list: {default_users}")
        logger.info(f"To configure users, set TRACKED_USERS environment variable or create {self.config_file}")
        
        return default_users
    
    def save_tracked_users(self, users: List[str]) -> bool:
        """
        Save list of users to configuration file.
        
        Args:
            users: List of riot_ids to track
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config = {
                "tracked_users": users,
                "last_updated": time.time(),
                "config_version": "1.0"
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved {len(users)} users to {self.config_file}")
            self._tracked_users = None  # Clear cache
            return True
            
        except Exception as e:
            logger.error(f"Failed to save users to {self.config_path}: {e}")
            return False
    
    def add_user(self, riot_id: str) -> bool:
        """
        Add a user to the tracked list.
        
        Args:
            riot_id: Riot ID in format "username#tag"
            
        Returns:
            True if added successfully, False if already exists or failed
        """
        current_users = self.get_tracked_users()
        
        if riot_id in current_users:
            logger.info(f"User {riot_id} already in tracked list")
            return False
        
        current_users.append(riot_id)
        return self.save_tracked_users(current_users)
    
    def remove_user(self, riot_id: str) -> bool:
        """
        Remove a user from the tracked list.
        
        Args:
            riot_id: Riot ID to remove
            
        Returns:
            True if removed successfully, False if not found or failed
        """
        current_users = self.get_tracked_users()
        
        if riot_id not in current_users:
            logger.info(f"User {riot_id} not in tracked list")
            return False
        
        current_users.remove(riot_id)
        return self.save_tracked_users(current_users)
    
    async def initialize_all_users(self, max_concurrent: int = 2) -> Dict[str, dict]:
        """
        Initialize data for all tracked users at application startup.
        
        This performs a comprehensive data load for each user, which can take
        15-30 minutes per user. Uses semaphore to limit concurrent operations.
        
        Args:
            max_concurrent: Maximum number of concurrent user initializations
            
        Returns:
            Dictionary mapping riot_id to initialization results
        """
        users = self.get_tracked_users()
        
        if not users:
            logger.warning("No users configured for initialization")
            return {}
        
        logger.info(f"Starting initialization for {len(users)} users with max {max_concurrent} concurrent")
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def init_single_user(riot_id: str) -> dict:
            """Initialize a single user with semaphore protection."""
            async with semaphore:
                logger.info(f"Starting initialization for user: {riot_id}")
                start_time = time.time()
                
                try:
                    # Import here to avoid circular imports
                    from .tracker_gg import load_full_api_data
                    
                    result = await load_full_api_data(riot_id, load_to_database=True)
                    
                    if result and result.get("status") != "error":
                        duration = (time.time() - start_time) / 60
                        logger.info(f"✅ User {riot_id} initialized successfully in {duration:.1f} minutes")
                        result["duration_minutes"] = duration
                        return result
                    else:
                        logger.error(f"❌ User {riot_id} initialization failed: {result}")
                        return {"status": "error", "error": "Initialization failed", "riot_id": riot_id}
                        
                except Exception as e:
                    duration = (time.time() - start_time) / 60
                    logger.error(f"❌ User {riot_id} initialization exception after {duration:.1f} minutes: {e}")
                    return {"status": "error", "error": str(e), "riot_id": riot_id}
        
        # Run all user initializations concurrently
        tasks = [init_single_user(riot_id) for riot_id in users]
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        
        for i, result in enumerate(completed_results):
            riot_id = users[i]
            
            if isinstance(result, Exception):
                logger.error(f"Exception during {riot_id} initialization: {result}")
                results[riot_id] = {"status": "error", "error": str(result)}
                failed += 1
            else:
                results[riot_id] = result
                if result.get("status") == "error":
                    failed += 1
                else:
                    successful += 1
        
        total_duration = sum(
            r.get("duration_minutes", 0) for r in results.values() 
            if isinstance(r, dict) and "duration_minutes" in r
        )
        
        logger.info(f"🎉 User initialization complete!")
        logger.info(f"📊 Total: {len(users)}, Successful: {successful}, Failed: {failed}")
        logger.info(f"⏱️  Total processing time: {total_duration:.1f} minutes")
        
        return results
    
    async def update_users_on_demand(self, riot_ids: List[str], priority_level: str = "high") -> Dict[str, dict]:
        """
        Update specific users with priority endpoints only (web-triggered updates).
        
        This is much faster than initialization (2-5 minutes per user) and focuses
        on recent/priority data only.
        
        Args:
            riot_ids: List of riot_ids to update
            priority_level: Priority level ("high", "medium", "low")
            
        Returns:
            Dictionary mapping riot_id to update results
        """
        if not riot_ids:
            return {}
        
        logger.info(f"Starting priority update for {len(riot_ids)} users (priority: {priority_level})")
        
        # Map priority levels to thresholds
        priority_map = {
            "high": 0.7,    # PRIORITY_HIGH
            "medium": 0.4,  # PRIORITY_MEDIUM  
            "low": 0.1      # PRIORITY_LOW
        }
        
        priority_threshold = priority_map.get(priority_level, 0.7)
        results = {}
        
        for riot_id in riot_ids:
            logger.info(f"Updating user: {riot_id}")
            start_time = time.time()
            
            try:
                # Import here to avoid circular imports
                from .tracker_gg import update_recent_data
                
                result = await update_recent_data(riot_id, priority_threshold, load_to_database=True)
                
                duration = (time.time() - start_time) / 60
                logger.info(f"✅ User {riot_id} updated in {duration:.1f} minutes")
                
                if result:
                    result["duration_minutes"] = duration
                    results[riot_id] = result
                else:
                    results[riot_id] = {"status": "error", "error": "Update failed", "riot_id": riot_id}
                    
            except Exception as e:
                duration = (time.time() - start_time) / 60
                logger.error(f"❌ User {riot_id} update failed after {duration:.1f} minutes: {e}")
                results[riot_id] = {"status": "error", "error": str(e), "riot_id": riot_id}
        
        successful = len([r for r in results.values() if r.get("status") != "error"])
        failed = len(riot_ids) - successful
        
        logger.info(f"🔄 User updates complete! Successful: {successful}, Failed: {failed}")
        
        return results
    
    def get_initialization_status(self) -> Dict[str, str]:
        """
        Get initialization status for all tracked users.
        
        Returns:
            Dictionary mapping riot_id to status ("initialized", "pending", "error")
        """
        # This would check database for existing data
        # For now, return placeholder
        users = self.get_tracked_users()
        return {user: "pending" for user in users}


# Global instance
user_manager = UserManager()


# Convenience functions for external use
def get_tracked_users() -> List[str]:
    """Get list of all tracked users."""
    return user_manager.get_tracked_users()


async def initialize_all_users(max_concurrent: int = 2) -> Dict[str, dict]:
    """Initialize all tracked users."""
    return await user_manager.initialize_all_users(max_concurrent)


async def update_users(riot_ids: List[str], priority: str = "high") -> Dict[str, dict]:
    """Update specific users with priority data."""
    return await user_manager.update_users_on_demand(riot_ids, priority)


def add_tracked_user(riot_id: str) -> bool:
    """Add a user to tracking list."""
    return user_manager.add_user(riot_id)


def remove_tracked_user(riot_id: str) -> bool:
    """Remove a user from tracking list."""
    return user_manager.remove_user(riot_id)