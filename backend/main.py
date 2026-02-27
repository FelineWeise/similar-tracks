import asyncio
import logging

import httpx
from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.deezer import fetch_track_info as deezer_fetch
from backend.lastfm import fetch_track_tags, get_similar_tracks, get_track_tags
from backend.models import SimilarTracksResponse, TrackInfo, TrackRequest
from backend.spotify import get_track_info, search_track

app = FastAPI(
    title="Similar Tracks Finder",
    description="Find songs similar to a given Spotify track using Last.fm collaborative filtering.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Always over-fetch from Last.fm so the client has a large pool to filter
OVERFETCH_LIMIT = 50


@app.post("/api/similar", response_model=SimilarTracksResponse)
async def api_similar(req: TrackRequest):
    # 1. Seed track from Spotify
    try:
        seed = await asyncio.to_thread(get_track_info, req.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {exc}")

    primary_artist = seed.artists[0]

    # 2. Last.fm: similar tracks + seed tags (run concurrently)
    try:
        lastfm_results, seed_tags = await asyncio.gather(
            asyncio.to_thread(get_similar_tracks, primary_artist, seed.name, OVERFETCH_LIMIT),
            asyncio.to_thread(get_track_tags, primary_artist, seed.name),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Last.fm API error: {exc}")

    # 3. Get seed BPM from Deezer
    async with httpx.AsyncClient() as client:
        seed_deezer = await deezer_fetch(client, primary_artist, seed.name)
    seed.bpm = seed_deezer.get("bpm")
    seed.tags = seed_tags
    if not seed.preview_url:
        seed.preview_url = seed_deezer.get("preview")

    # 4. Enrich each result concurrently: Spotify metadata + Deezer BPM/preview + Last.fm tags
    async with httpx.AsyncClient() as client:
        async def enrich(item: dict) -> TrackInfo | None:
            artist_name = item["artist"]
            track_name = item["name"]
            match_score = item["match"]

            # Run all enrichment in parallel for this track
            sp_future = asyncio.to_thread(search_track, artist_name, track_name)
            dz_future = deezer_fetch(client, artist_name, track_name)
            tag_future = fetch_track_tags(client, artist_name, track_name)

            sp_track, dz_info, tags = await asyncio.gather(
                sp_future, dz_future, tag_future
            )

            if sp_track:
                sp_track.match_score = match_score
                sp_track.bpm = dz_info.get("bpm")
                sp_track.tags = tags
                if not sp_track.preview_url:
                    sp_track.preview_url = dz_info.get("preview")
                return sp_track
            else:
                return TrackInfo(
                    name=track_name,
                    artists=[artist_name],
                    album="",
                    album_art=item.get("image"),
                    preview_url=dz_info.get("preview"),
                    spotify_url=None,
                    match_score=match_score,
                    bpm=dz_info.get("bpm"),
                    tags=tags,
                )

        results = await asyncio.gather(*(enrich(item) for item in lastfm_results))
        similar = [r for r in results if r is not None]

    return SimilarTracksResponse(
        seed_track=seed,
        similar_tracks=similar,
        seed_tags=seed_tags,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug/tags")
def debug_tags(artist: str, track: str):
    """Diagnostic endpoint: test Last.fm tag fetching for a single track."""
    import httpx as _httpx
    from backend.config import LASTFM_API_KEY as _key

    params = {
        "method": "track.gettoptags",
        "artist": artist,
        "track": track,
        "api_key": _key,
        "format": "json",
        "autocorrect": 1,
    }
    resp = _httpx.get("https://ws.audioscrobbler.com/2.0/", params=params, timeout=10)
    raw = resp.json()
    parsed = get_track_tags(artist, track)
    return {"raw_response": raw, "parsed_tags": parsed}


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
