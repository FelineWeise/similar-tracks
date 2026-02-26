from pydantic import BaseModel, Field


class SimilarityWeights(BaseModel):
    bpm: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for tempo/BPM similarity")
    vocals: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for vocal presence")
    instrumentals: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for instrumentalness")
    style: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for style (danceability + energy)")
    mood: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for mood/valence")


class TrackRequest(BaseModel):
    url: str = Field(description="Spotify track URL or URI")
    weights: SimilarityWeights = Field(default_factory=SimilarityWeights)
    limit: int = Field(default=10, ge=1, le=50, description="Number of similar tracks to return")


class AudioFeatures(BaseModel):
    bpm: float
    energy: float
    danceability: float
    valence: float
    instrumentalness: float
    speechiness: float
    acousticness: float
    liveness: float


class TrackInfo(BaseModel):
    name: str
    artists: list[str]
    album: str
    album_art: str | None = None
    preview_url: str | None = None
    spotify_url: str
    audio_features: AudioFeatures | None = None


class SimilarTracksResponse(BaseModel):
    seed_track: TrackInfo
    similar_tracks: list[TrackInfo]
