import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
from contextlib import asynccontextmanager
from databases import Database

from scrapers.valorant_scraper import fetch_valorant_player_stats
from models.valorant_model import ValorantPlayerStats

from models.db import SessionLocal, create_db

from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "Please set DATABASE_URL environment variable")
database = Database(DATABASE_URL)





# Define a lifespan function for managing startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to manage app lifecycle events.
    """

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    await FastAPILimiter.init(redis_client)

    # Retry database connection with exponential backoff
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
            await database.connect()
            print("Successfully connected to database!")
            break
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                print("Max retries reached. Database connection failed.")
                raise
            print(f"Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

    create_db()

    yield

    await redis_client.close()
    await database.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get(
    "/valorant/player/{username}/current",
    response_model=ValorantPlayerStats,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def get_valorant_current_act_stats(username: str):
    player_stats = await fetch_valorant_player_stats(
        username=username, season="current"
    )
    if player_stats is None:
        raise HTTPException(
            status_code=404, detail=f"Player stats not found for username: {username}."
        )
    player_stats.season = "Current Act"
    return player_stats


@app.get(
    "/valorant/player/{username}/all",
    response_model=ValorantPlayerStats,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def get_valorant_all_seasons_stats(
    username: str
):
    player_stats = await fetch_valorant_player_stats(username=username, season="all")
    if player_stats is None:
        raise HTTPException(
            status_code=404, detail=f"Player stats not found for username: {username}."
        )
    player_stats.season = "All Acts"
    return player_stats


@app.get("/status", summary="API Health Check")
async def status():
    return {"status": "ok"}



