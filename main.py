import os
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

    await database.connect()

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
async def get_valorant_current_act_stats(
    username: str, api_key: str = Depends(get_api_key)
):
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


# @app.post(
#     "/admin/create-api-key",
#     summary="Create a new API Key",
# )
# async def create_new_api_key(
#     user: str,
#     permission: str = "normal",
#     db: Session = Depends(get_session_local),
#     admin_api_key_object: APIKey = Depends(get_admin_api_key),
# ) -> dict:
#     """
#     Create a new API key, but only accessible to users with 'admin' permissions.
#     """
    # The get_admin_api_key dependency has already verified that admin_api_key_object is a valid admin key.

    if permission not in ["normal", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid permission level specified for the new key.")

    new_plaintext_key = generate_random_api_key()
    try:
        # add_api_key handles hashing internally
        add_api_key(db, new_plaintext_key, user, permission)
        return {
            "message": f"API Key for user '{user}' created successfully. This is the only time you will see the key.",
            "api_key": new_plaintext_key,  # Show plaintext key once upon creation
            "user": user,
            "permission": permission,
        }
    except Exception as e:
        db.rollback() # Rollback in case of failure during add_api_key
        # Propagate the specific error from add_api_key (e.g., if a hash collision occurred, though unlikely with SHA256)
        raise HTTPException(status_code=400, detail=f"Failed to create API key: {str(e)}")
