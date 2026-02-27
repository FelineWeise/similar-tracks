from pydantic import BaseModel, Field


class TrackRequest(BaseModel):
    url: str = Field(description="Spotify track URL or URI")
    limit: int = Field(default=10, ge=1, le=50, description="Number of similar tracks to return")


class TrackInfo(BaseModel):
    name: str
    artists: list[str]
    album: str
    album_art: str | None = None
    preview_url: str | None = None
    spotify_url: str | None = None
    match_score: float | None = None


class SimilarTracksResponse(BaseModel):
    seed_track: TrackInfo
    similar_tracks: list[TrackInfo]
