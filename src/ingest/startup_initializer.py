"""
Startup Initialization System

This module handles the automatic initialization of all user data when the application starts.
It ensures that all tracked users have their data loaded into the database before the API
becomes available for updates.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Optional

from .user_manager import user_manager
from ..shared.utils import get_logger

logger = get_logger(__name__)


class StartupInitializer:
    """Handles initialization of all user data at application startup."""
    
    def __init__(self):
        """Initialize the startup system."""
        self.initialization_complete = False
        self.initialization_results: Optional[Dict[str, dict]] = None
        self.initialization_start_time: Optional[float] = None
        
    async def run_full_initialization(self, max_concurrent: int = 2) -> Dict[str, dict]:
        """
        Run complete initialization of all tracked users.
        
        This is called at application startup to ensure all user data is loaded
        into the database before the API becomes available for updates.
        
        Args:
            max_concurrent: Maximum number of concurrent user initializations
            
        Returns:
            Dictionary with initialization results for each user
        """
        if self.initialization_complete:
            logger.info("Initialization already completed")
            return self.initialization_results or {}
        
        logger.info("🚀 Starting full user initialization at application startup")
        self.initialization_start_time = time.time()
        
        try:
            # Get all tracked users
            users = user_manager.get_tracked_users()
            
            if not users:
                logger.warning("No users configured for initialization")
                self.initialization_complete = True
                self.initialization_results = {}
                return {}
            
            logger.info(f"Initializing {len(users)} users: {', '.join(users)}")
            
            # Check if initialization should be skipped
            if os.getenv("SKIP_USER_INIT", "false").lower() == "true":
                logger.info("User initialization skipped due to SKIP_USER_INIT=true")
                self.initialization_complete = True
                self.initialization_results = {user: {"status": "skipped"} for user in users}
                return self.initialization_results
            
            # Run initialization for all users
            results = await user_manager.initialize_all_users(max_concurrent)
            
            # Calculate summary statistics
            total_time = (time.time() - self.initialization_start_time) / 60
            successful = len([r for r in results.values() if r.get("status") != "error"])
            failed = len(users) - successful
            
            logger.info("🎉 Startup initialization completed!")
            logger.info(f"📊 Results: {successful} successful, {failed} failed")
            logger.info(f"⏱️  Total time: {total_time:.1f} minutes")
            
            # Store results
            self.initialization_results = results
            self.initialization_complete = True
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Startup initialization failed: {e}")
            # Mark as complete even on failure to prevent retries
            self.initialization_complete = True
            self.initialization_results = {"error": str(e)}
            raise
    
    async def run_background_initialization(self, max_concurrent: int = 1) -> None:
        """
        Run initialization in the background without blocking API startup.
        
        This allows the API to start immediately while user data loads in the background.
        Use this approach when you want the API to be responsive immediately.
        
        Args:
            max_concurrent: Maximum concurrent user initializations (lower for background)
        """
        logger.info("🔄 Starting background user initialization")
        
        try:
            await self.run_full_initialization(max_concurrent)
        except Exception as e:
            logger.error(f"Background initialization failed: {e}")
    
    def get_initialization_status(self) -> Dict[str, any]:
        """
        Get current initialization status.
        
        Returns:
            Dictionary with status information
        """
        if not self.initialization_start_time:
            return {
                "status": "not_started",
                "complete": False,
                "users_initialized": 0,
                "total_users": len(user_manager.get_tracked_users())
            }
        
        status = {
            "status": "completed" if self.initialization_complete else "in_progress",
            "complete": self.initialization_complete,
            "start_time": self.initialization_start_time,
            "total_users": len(user_manager.get_tracked_users())
        }
        
        if self.initialization_complete:
            status["completion_time"] = time.time()
            status["duration_minutes"] = (status["completion_time"] - self.initialization_start_time) / 60
            
            if self.initialization_results:
                status["users_initialized"] = len([
                    r for r in self.initialization_results.values() 
                    if isinstance(r, dict) and r.get("status") != "error"
                ])
                status["users_failed"] = len([
                    r for r in self.initialization_results.values() 
                    if isinstance(r, dict) and r.get("status") == "error"
                ])
                status["results"] = self.initialization_results
        else:
            status["current_duration_minutes"] = (time.time() - self.initialization_start_time) / 60
        
        return status
    
    def is_initialization_complete(self) -> bool:
        """Check if initialization has completed."""
        return self.initialization_complete
    
    def wait_for_initialization(self, timeout: float = 1800) -> bool:
        """
        Wait for initialization to complete (blocking).
        
        Args:
            timeout: Maximum time to wait in seconds (default: 30 minutes)
            
        Returns:
            True if initialization completed, False if timeout
        """
        start_time = time.time()
        
        while not self.initialization_complete:
            if time.time() - start_time > timeout:
                logger.warning(f"Initialization wait timeout after {timeout} seconds")
                return False
            
            time.sleep(5)  # Check every 5 seconds
        
        return True


# Global instance
startup_initializer = StartupInitializer()


# Convenience functions
async def initialize_all_users_at_startup(max_concurrent: int = 2) -> Dict[str, dict]:
    """Initialize all users at application startup."""
    return await startup_initializer.run_full_initialization(max_concurrent)


async def initialize_users_in_background(max_concurrent: int = 1) -> None:
    """Initialize users in background without blocking API startup."""
    await startup_initializer.run_background_initialization(max_concurrent)


def get_startup_status() -> Dict[str, any]:
    """Get current startup initialization status."""
    return startup_initializer.get_initialization_status()


def is_startup_complete() -> bool:
    """Check if startup initialization is complete."""
    return startup_initializer.is_initialization_complete()