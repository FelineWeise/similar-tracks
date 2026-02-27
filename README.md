# Similar Tracks Finder

A web app that finds songs similar to a given Spotify track using Last.fm's collaborative filtering — powered by 20+ years of real listener data.

## Features

- **Spotify URL input** – paste any Spotify track link
- **Last.fm similarity** – finds tracks that listeners of the seed track also enjoy, with match scores
- **30-second preview playback** via Deezer (fallback when Spotify previews are unavailable)
- **Spotify cross-referencing** – results link back to Spotify with album art
- Configurable result count (5 / 10 / 20 / 50)

## Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- A **Spotify Developer** application (free) — create one at https://developer.spotify.com/dashboard
- A **Last.fm API key** (free) — create one at https://www.last.fm/api/account/create

## Setup

```bash
# Clone the repo
cd /Users/feline/Desktop/Repositories
git clone https://github.com/FelineWeise/similar-tracks.git
cd similar-tracks

# Install dependencies
poetry install

# Configure credentials
cp .env.example .env
# Edit .env and add your Spotify Client ID/Secret and Last.fm API Key
```

## Running

```bash
poetry run python run.py
```

Open http://localhost:8000 in your browser.

## API

### `POST /api/similar`

**Request body:**

```json
{
  "url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
  "limit": 10
}
```

**Response:** JSON with `seed_track` and `similar_tracks`, each containing name, artists, album, album art, Spotify URL, match score, and preview URL.

## How It Works

1. **Spotify** resolves the pasted URL to track metadata (name, artist, album art)
2. **Last.fm** `track.getSimilar` returns similar tracks based on collaborative listening patterns
3. Each result is cross-referenced on **Spotify** for album art and links
4. **Deezer** provides 30-second audio previews as a fallback

## Tech Stack

- **Backend:** Python, FastAPI, Spotipy, httpx
- **Frontend:** Vanilla HTML / CSS / JS
- **APIs:** Spotify Web API (track lookup), Last.fm (similarity), Deezer (audio previews)

## License

MIT
