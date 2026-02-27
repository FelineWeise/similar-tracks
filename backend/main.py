from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.deezer import get_preview_url
from backend.lastfm import get_similar_tracks
from backend.models import SimilarTracksResponse, TrackInfo, TrackRequest
from backend.spotify import get_track_info, search_track

app = FastAPI(
    title="Similar Tracks Finder",
    description="Find songs similar to a given Spotify track using Last.fm collaborative filtering.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/similar", response_model=SimilarTracksResponse)
def api_similar(req: TrackRequest):
    # 1. Look up seed track on Spotify (sp.track still works)
    try:
        seed = get_track_info(req.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {exc}")

    # 2. Ask Last.fm for similar tracks
    try:
        lastfm_results = get_similar_tracks(
            artist=seed.artists[0],
            track=seed.name,
            limit=req.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Last.fm API error: {exc}")

    # 3. Enrich each result with Spotify metadata + Deezer preview
    similar: list[TrackInfo] = []
    for item in lastfm_results:
        artist_name = item["artist"]
        track_name = item["name"]
        match_score = item["match"]

        # Try Spotify search for album art + link
        sp_track = search_track(artist_name, track_name)

        if sp_track:
            sp_track.match_score = match_score
            # If Spotify didn't provide a preview, try Deezer
            if not sp_track.preview_url:
                sp_track.preview_url = get_preview_url(artist_name, track_name)
            similar.append(sp_track)
        else:
            # Fallback: use Last.fm data directly
            preview = get_preview_url(artist_name, track_name)
            similar.append(TrackInfo(
                name=track_name,
                artists=[artist_name],
                album="",
                album_art=item.get("image"),
                preview_url=preview,
                spotify_url=None,
                match_score=match_score,
            ))

    return SimilarTracksResponse(seed_track=seed, similar_tracks=similar)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the frontend as static files (mounted last so API routes take priority)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
