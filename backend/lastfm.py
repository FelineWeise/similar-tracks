import httpx

from backend.config import LASTFM_API_KEY

LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"


def get_similar_tracks(
    artist: str, track: str, limit: int = 10
) -> list[dict]:
    """Call Last.fm track.getSimilar and return a list of similar tracks.

    Each dict has keys: name, artist, match (0.0-1.0), image, url.
    """
    if not LASTFM_API_KEY:
        raise ValueError(
            "Last.fm API key not configured. "
            "Set LASTFM_API_KEY in your .env file."
        )

    params = {
        "method": "track.getsimilar",
        "artist": artist,
        "track": track,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": limit,
    }

    resp = httpx.get(LASTFM_BASE, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise ValueError(f"Last.fm error: {data.get('message', 'Unknown error')}")

    raw_tracks = data.get("similartracks", {}).get("track", [])
    results = []
    for t in raw_tracks:
        # Pick the largest image available
        images = t.get("image", [])
        image_url = None
        for img in reversed(images):
            if img.get("#text"):
                image_url = img["#text"]
                break

        artist_name = t.get("artist", {}).get("name", "") if isinstance(t.get("artist"), dict) else str(t.get("artist", ""))

        results.append({
            "name": t.get("name", ""),
            "artist": artist_name,
            "match": float(t.get("match", 0)),
            "image": image_url,
            "url": t.get("url", ""),
        })

    return results
