from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.models import SimilarTracksResponse, TrackRequest
from backend.spotify import find_similar_tracks

app = FastAPI(
    title="Similar Tracks Finder",
    description="Find songs similar to a given Spotify track, with configurable similarity weights.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/similar", response_model=SimilarTracksResponse)
def get_similar_tracks(req: TrackRequest):
    try:
        seed, similar = find_similar_tracks(req.url, req.weights, req.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {exc}")
    return SimilarTracksResponse(seed_track=seed, similar_tracks=similar)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the frontend as static files (mounted last so API routes take priority)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
