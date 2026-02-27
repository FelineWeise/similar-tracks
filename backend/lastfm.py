import asyncio

import httpx

from backend.config import LASTFM_API_KEY

LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"
# Last.fm allows 5 req/s averaged over 5 min; semaphore limits concurrency
_sem = asyncio.Semaphore(4)


def _check_key():
    if not LASTFM_API_KEY:
        raise ValueError(
            "Last.fm API key not configured. "
            "Set LASTFM_API_KEY in your .env file."
        )


def get_similar_tracks(artist: str, track: str, limit: int = 50) -> list[dict]:
    """Call Last.fm track.getSimilar (sync). Returns list of dicts with
    keys: name, artist, match, image, url."""
    _check_key()
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
        images = t.get("image", [])
        image_url = None
        for img in reversed(images):
            if img.get("#text"):
                image_url = img["#text"]
                break

        artist_info = t.get("artist")
        artist_name = artist_info.get("name", "") if isinstance(artist_info, dict) else str(artist_info or "")

        results.append({
            "name": t.get("name", ""),
            "artist": artist_name,
            "match": float(t.get("match", 0)),
            "image": image_url,
            "url": t.get("url", ""),
        })
    return results


def get_track_tags(artist: str, track: str, limit: int = 20) -> list[str]:
    """Fetch top tags for a track (sync, single call)."""
    _check_key()
    params = {
        "method": "track.gettoptags",
        "artist": artist,
        "track": track,
        "api_key": LASTFM_API_KEY,
        "format": "json",
    }
    try:
        resp = httpx.get(LASTFM_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        tags = data.get("toptags", {}).get("tag", [])
        return [t["name"].lower() for t in tags[:limit] if int(t.get("count", 0)) > 0]
    except Exception:
        return []


async def fetch_track_tags(client: httpx.AsyncClient, artist: str, track: str) -> list[str]:
    """Async version of tag fetch for bulk enrichment."""
    async with _sem:
        params = {
            "method": "track.gettoptags",
            "artist": artist,
            "track": track,
            "api_key": LASTFM_API_KEY,
            "format": "json",
        }
        try:
            resp = await client.get(LASTFM_BASE, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            tags = data.get("toptags", {}).get("tag", [])
            return [t["name"].lower() for t in tags[:15] if int(t.get("count", 0)) > 0]
        except Exception:
            return []
