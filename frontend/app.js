(() => {
  const form = document.getElementById("search-form");
  const urlInput = document.getElementById("track-url");
  const searchBtn = document.getElementById("search-btn");
  const seedEl = document.getElementById("seed-track");
  const resultsEl = document.getElementById("results");
  const errorEl = document.getElementById("error");
  const loadingEl = document.getElementById("loading");
  const filterPanel = document.getElementById("filter-panel");
  const bpmFilter = document.getElementById("bpm-filter");
  const bpmSlider = document.getElementById("bpm-tolerance");
  const bpmLabel = document.getElementById("bpm-label");
  const tagFilter = document.getElementById("tag-filter");
  const tagChips = document.getElementById("tag-chips");

  let currentAudio = null;

  // Full result pool from the API (up to 50 enriched tracks)
  let allTracks = [];
  let seedTrack = null;
  let seedTags = [];
  let selectedTags = new Set();
  let displayLimit = 10;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await search();
  });

  // Re-rank when filters change
  bpmSlider.addEventListener("input", () => {
    updateBpmLabel();
    renderFiltered();
  });

  function updateBpmLabel() {
    const val = parseInt(bpmSlider.value, 10);
    if (val >= 100) {
      bpmLabel.textContent = "Any";
    } else if (val === 0) {
      bpmLabel.textContent = "Exact";
    } else {
      bpmLabel.textContent = "\u00b1" + val + "%";
    }
  }

  async function search() {
    const url = urlInput.value.trim();
    if (!url) return;
    displayLimit = parseInt(document.getElementById("limit").value, 10);

    stopAudio();
    seedEl.classList.add("hidden");
    filterPanel.classList.add("hidden");
    resultsEl.innerHTML = "";
    errorEl.classList.add("hidden");
    loadingEl.classList.remove("hidden");
    searchBtn.disabled = true;
    allTracks = [];
    seedTrack = null;
    seedTags = [];
    selectedTags.clear();

    try {
      const resp = await fetch("/api/similar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, limit: 50 }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed (${resp.status})`);
      }

      const data = await resp.json();
      seedTrack = data.seed_track;
      allTracks = data.similar_tracks;
      seedTags = data.seed_tags || [];

      console.log("[debug] seed_tags:", seedTags);
      console.log("[debug] tracks with tags:", allTracks.filter(t => t.tags && t.tags.length > 0).length, "/", allTracks.length);

      renderSeed(seedTrack);
      buildFilters();
      renderFiltered();
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.classList.remove("hidden");
    } finally {
      loadingEl.classList.add("hidden");
      searchBtn.disabled = false;
    }
  }

  function buildFilters() {
    // Collect all unique tags across seed + result tracks
    const tagCounts = {};
    for (const tag of seedTags) {
      tagCounts[tag] = (tagCounts[tag] || 0) + 5; // boost seed tags
    }
    for (const t of allTracks) {
      for (const tag of (t.tags || [])) {
        tagCounts[tag] = (tagCounts[tag] || 0) + 1;
      }
    }

    // Sort by frequency, take top 30
    const sortedTags = Object.entries(tagCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 30)
      .map(([tag]) => tag);

    // BPM filter: only show if seed has BPM
    if (seedTrack && seedTrack.bpm) {
      bpmFilter.classList.remove("hidden");
      bpmSlider.value = 100;
      updateBpmLabel();
    } else {
      bpmFilter.classList.add("hidden");
    }

    // Tag chips
    if (sortedTags.length > 0) {
      tagFilter.classList.remove("hidden");
      tagChips.innerHTML = "";
      for (const tag of sortedTags) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "tag-chip";
        chip.textContent = tag;
        chip.addEventListener("click", () => {
          if (selectedTags.has(tag)) {
            selectedTags.delete(tag);
            chip.classList.remove("active");
          } else {
            selectedTags.add(tag);
            chip.classList.add("active");
          }
          renderFiltered();
        });
        tagChips.appendChild(chip);
      }
    } else {
      tagFilter.classList.add("hidden");
    }

    filterPanel.classList.remove("hidden");
  }

  function rankTracks() {
    const bpmTol = parseInt(bpmSlider.value, 10);
    const hasBpmFilter = seedTrack && seedTrack.bpm && bpmTol < 100;
    const hasTagFilter = selectedTags.size > 0;

    return allTracks
      .map((t) => {
        let score = t.match_score || 0;

        // BPM scoring
        if (hasBpmFilter && t.bpm) {
          const pctDiff = (Math.abs(t.bpm - seedTrack.bpm) / seedTrack.bpm) * 100;
          if (bpmTol === 0) {
            // Exact: only allow within 2%
            score *= pctDiff <= 2 ? 1.0 : 0;
          } else if (pctDiff > bpmTol) {
            score = 0; // outside tolerance, filter out
          } else {
            // Within tolerance: boost closer matches
            score *= 1 - (pctDiff / bpmTol) * 0.4;
          }
        }

        // Tag scoring
        if (hasTagFilter && t.tags && t.tags.length > 0) {
          const trackTags = new Set(t.tags);
          let overlap = 0;
          for (const tag of selectedTags) {
            if (trackTags.has(tag)) overlap++;
          }
          const tagRatio = overlap / selectedTags.size;
          // Multiply by tag ratio (0 = no overlap → score halved; 1 = full overlap → unchanged)
          score *= 0.5 + 0.5 * tagRatio;
        } else if (hasTagFilter) {
          // Track has no tags: penalize slightly
          score *= 0.4;
        }

        return { ...t, _score: score };
      })
      .filter((t) => t._score > 0)
      .sort((a, b) => b._score - a._score);
  }

  function renderFiltered() {
    const ranked = rankTracks();
    const shown = ranked.slice(0, displayLimit);
    renderResults(shown, ranked.length);
  }

  function matchBadge(score) {
    if (score == null) return "";
    const pct = Math.round(score * 100);
    return `<span class="match-badge">${pct}% match</span>`;
  }

  function bpmBadge(bpm) {
    if (!bpm) return "";
    return `<span class="bpm-badge">${Math.round(bpm)} BPM</span>`;
  }

  function renderSeed(track) {
    const spotifyLink = track.spotify_url
      ? `<a href="${track.spotify_url}" target="_blank" rel="noopener">${esc(track.name)}</a>`
      : esc(track.name);
    const bpm = track.bpm ? `<span class="seed-bpm">${Math.round(track.bpm)} BPM</span>` : "";
    seedEl.innerHTML = `
      ${track.album_art ? `<img src="${track.album_art}" alt="Album art" />` : ""}
      <div class="seed-meta">
        <h2>${spotifyLink}</h2>
        <div class="artists">${esc(track.artists.join(", "))} &mdash; ${esc(track.album)}</div>
        ${bpm}
      </div>
    `;
    seedEl.classList.remove("hidden");
  }

  function renderResults(tracks, totalAvailable) {
    if (!tracks.length) {
      resultsEl.innerHTML = "<p>No tracks match your filters. Try loosening the constraints.</p>";
      return;
    }
    const countNote = totalAvailable > tracks.length
      ? ` (showing ${tracks.length} of ${totalAvailable})`
      : ` (${tracks.length})`;
    let html = `<h3>Similar Tracks${countNote}</h3>`;
    tracks.forEach((t) => {
      const previewBtn = t.preview_url
        ? `<button class="play-btn" data-url="${t.preview_url}" title="Preview">&#9654;</button>`
        : "";
      const nameLink = t.spotify_url
        ? `<a href="${t.spotify_url}" target="_blank" rel="noopener">${esc(t.name)}</a>`
        : esc(t.name);
      html += `
        <div class="track-card">
          ${t.album_art ? `<img src="${t.album_art}" alt="" />` : '<div class="img-placeholder"></div>'}
          <div class="track-info">
            <div class="name">${nameLink}</div>
            <div class="detail">${esc(t.artists.join(", "))}${t.album ? " &mdash; " + esc(t.album) : ""}</div>
          </div>
          <div class="track-badges">
            ${matchBadge(t.match_score)}
            ${bpmBadge(t.bpm)}
          </div>
          ${previewBtn}
        </div>
      `;
    });
    resultsEl.innerHTML = html;

    resultsEl.querySelectorAll(".play-btn").forEach((btn) => {
      btn.addEventListener("click", () => togglePreview(btn));
    });
  }

  function togglePreview(btn) {
    const url = btn.dataset.url;
    if (currentAudio && currentAudio.src === url) {
      stopAudio();
      return;
    }
    stopAudio();
    currentAudio = new Audio(url);
    currentAudio.volume = 0.5;
    currentAudio.play();
    btn.innerHTML = "&#9724;";
    currentAudio.addEventListener("ended", () => {
      btn.innerHTML = "&#9654;";
      currentAudio = null;
    });
  }

  function stopAudio() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
      document.querySelectorAll(".play-btn").forEach((b) => {
        b.innerHTML = "&#9654;";
      });
    }
  }

  function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }
})();
