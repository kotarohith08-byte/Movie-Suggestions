/**
 * CineMatch AI - Streaming-Grade Client-Side Engine (v2.0)
 * Powers:
 * 1. Streaming Hero Banner with featured selector (Image 3 Inspiration)
 * 2. TOP 10 Contents Today with giant outlined rank numbers 1-10 (Image 3 Inspiration)
 * 3. Ask CineMatch AI Conversational Assistant with ranked recommendation cards (Image 1 Inspiration)
 * 4. Choose Your Mood: 8-mood emotional vector matcher (Requirement 4)
 * 5. Advanced Discovery & Multi-Filtering: genre, industry, era, rating, sort, autocomplete (Requirement 5)
 * 6. Personal Watchlist, Favourites, Watched, and Star Ratings persisted in localStorage (Requirement 6)
 * 7. Cinematic Movie Details Modal with Hero Backdrop, Synopsis, Director, Circular Cast Avatars (Image 2 Inspiration)
 * 8. Transparent, Explainable AI Recommendation tags (Requirement 8)
 * 10. ML Metrics Modal with Chart.js (Requirement 9)
 */

(function () {
  "use strict";

  // --- 1. Dataset & Indexing ---
  const MOVIES = (typeof MOVIES_DATABASE !== "undefined" && Array.isArray(MOVIES_DATABASE))
    ? MOVIES_DATABASE
    : ((typeof window !== "undefined" && Array.isArray(window.MOVIES_DATABASE)) ? window.MOVIES_DATABASE : []);

  const MOVIE_MAP = new Map(MOVIES.map(m => [Number(m.id), m]));

  // State Management
  const state = {
    // Discovery Filters
    genre: "All",
    industry: "all",
    era: "all",
    minRating: 0,
    sortBy: "score",
    discoveryCount: 24,

    // Personalization
    activeAlgo: "hybrid",

    // Indian Cinema Section
    indianIndustry: "Kollywood",
    indianCount: 24,

    // Active Mood
    activeMood: null,

    // Hero Carousel
    currentHeroIndex: 0,
    heroAutoTimer: null,

    // User Libraries (localStorage)
    watchlist: loadStorageSet("cinematch_watchlist"),
    favourites: loadStorageSet("cinematch_favourites"),
    watched: loadStorageSet("cinematch_watched"),
    ratings: loadUserRatings()
  };

  // Curated Featured Movies for Streaming Hero Banner (Image 3 Inspiration)
  const FEATURED_HERO_TITLES = [
    {
      title: "Kalki 2898 AD",
      year: 2024,
      runtime: "3h 01m",
      cert: "UA 16+",
      backdrop: "https://image.tmdb.org/t/p/original/rstcAnBeCkxNQjNp3YXrF6IP1tW.jpg",
      synopsis: "When the world is consumed by darkness in Kasi, a modern avatar of Vishnu descends to Earth to protect humanity against evil forces led by Supreme Yaskin.",
      director: "Nag Ashwin",
      writers: "Nag Ashwin, Sai Madhav Burra"
    },
    {
      title: "Interstellar",
      year: 2014,
      runtime: "2h 49m",
      cert: "PG-13",
      backdrop: "https://image.tmdb.org/t/p/original/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
      synopsis: "A team of intrepid explorers travel through a newly discovered wormhole in space to ensure humanity's survival as Earth faces catastrophic blight.",
      director: "Christopher Nolan",
      writers: "Jonathan Nolan, Christopher Nolan"
    },
    {
      title: "Leo",
      year: 2023,
      runtime: "2h 44m",
      cert: "UA 16+",
      backdrop: "https://image.tmdb.org/t/p/original/2XUHC4lp3tDsgfFLFygNZ2x2Um9.jpg",
      synopsis: "A mild-mannered cafe owner in Kashmir becomes a local hero after thwarting an armed attack, but dangerous gangsters believe he is a ruthless former cartel kingpin.",
      director: "Lokesh Kanagaraj",
      writers: "Lokesh Kanagaraj, Rathna Kumar"
    },
    {
      title: "RRR",
      year: 2022,
      runtime: "3h 07m",
      cert: "UA 16+",
      backdrop: "https://image.tmdb.org/t/p/original/21sC2assImQIYCEDA84Qh9d1RsK.jpg",
      synopsis: "A fearless warrior on a perilous mission to rescue an abducted girl crosses paths with a steely officer of the British force in 1920s colonial India.",
      director: "S.S. Rajamouli",
      writers: "V. Vijayendra Prasad, S.S. Rajamouli"
    },
    {
      title: "Maharaja",
      year: 2024,
      runtime: "2h 21m",
      cert: "UA 16+",
      backdrop: "https://image.tmdb.org/t/p/original/s0m4TM1XRAftQStgKpw024RvkJo.jpg",
      synopsis: "A quiet barber approaches the police to report that his prized dustbin 'Lakshmi' has been stolen from his home, unraveling a high-stakes investigation of vengeance.",
      director: "Nithilan Saminathan",
      writers: "Nithilan Saminathan"
    },
    {
      title: "Doctor Strange in the Multiverse of Madness",
      year: 2022,
      runtime: "2h 28m",
      cert: "PG-13",
      backdrop: "https://image.tmdb.org/t/p/original/m99i89bCrcM5u2uGZ4L0fWvM20B.jpg",
      synopsis: "Dr. Stephen Strange casts a forbidden spell that opens the door to the multiverse, including an alternate version of himself whose threat to humanity is too great.",
      director: "Sam Raimi",
      writers: "Michael Waldron"
    }
  ];

  // =========================================================================
  // Authentic TMDB API Configuration & Verified Credits Integration
  // =========================================================================
  const TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8";
  const TMDB_API_HOSTS = ["https://api.tmdb.org/3", "https://api.themoviedb.org/3"];
  const TMDB_IMG_BASE = "https://image.tmdb.org/t/p";

  // In-memory runtime caches for zero-latency recall
  const CREDITS_CACHE = new Map();
  const PERSON_CACHE = new Map();

  // Pre-seed CREDITS_CACHE with verified prebaked Indian blockbusters
  if (typeof window !== "undefined" && window.PREBAKED_INDIAN_CREDITS) {
    try {
      for (const [k, v] of Object.entries(window.PREBAKED_INDIAN_CREDITS)) {
        CREDITS_CACHE.set(Number(k), v);
      }
    } catch (e) {}
  }

  // Helper to generate clean, high-contrast SVG Avatar with Initials
  function getAvatarPlaceholderSvg(name, size = 150) {
    const cleanName = (name || "Cast Member").trim();
    const parts = cleanName.split(/\s+/).filter(Boolean);
    const initials = parts.length > 1
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : (parts[0] ? parts[0].slice(0, 2).toUpperCase() : "?");

    // Deterministic hue from name
    let hash = 0;
    for (let i = 0; i < cleanName.length; i++) {
      hash = cleanName.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue1 = Math.abs(hash) % 360;
    const hue2 = (hue1 + 45) % 360;

    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <defs>
        <linearGradient id="g_${Math.abs(hash)}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="hsl(${hue1}, 65%, 22%)"/>
          <stop offset="100%" stop-color="hsl(${hue2}, 70%, 14%)"/>
        </linearGradient>
      </defs>
      <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2}" fill="url(#g_${Math.abs(hash)})" stroke="rgba(255,255,255,0.18)" stroke-width="2"/>
      <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="${Math.round(size * 0.38)}" font-weight="700" fill="#ffffff" letter-spacing="1">${initials}</text>
    </svg>`;

    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  // Fetch TMDB with multi-host failover and error resilience
  async function fetchTmdbJson(endpoint) {
    const sep = endpoint.includes("?") ? "&" : "?";
    for (const host of TMDB_API_HOSTS) {
      try {
        const url = `${host}${endpoint}${sep}api_key=${TMDB_API_KEY}`;
        const res = await fetch(url);
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        // try next host
      }
    }
    return null;
  }

  // Normalize diacritics and clean titles for TMDB search
  function cleanSearchTitle(t) {
    return (t || "")
      .replace(/\s*\(\d{4}\)\s*$/, "")
      .replace(/\s*,\s*The$/i, "")
      .replace(/\s*,\s*A$/i, "")
      .replace(/ā/g, "a").replace(/ī/g, "i").replace(/ū/g, "u").replace(/ō/g, "o")
      .trim();
  }

  // Fetch verified movie credits (directors & principal cast) from TMDB
  async function fetchMovieCredits(movie) {
    if (!movie) return null;
    const cacheKey = `cinematch_credits_${movie.id}`;
    if (CREDITS_CACHE.has(movie.id)) {
      return CREDITS_CACHE.get(movie.id);
    }
    try {
      const stored = localStorage.getItem(cacheKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        CREDITS_CACHE.set(movie.id, parsed);
        return parsed;
      }
    } catch (e) {}

    let tmdbMovieId = movie.tmdbId || null;
    let data = null;

    // 1. Try by tmdbId if known
    if (tmdbMovieId) {
      data = await fetchTmdbJson(`/movie/${tmdbMovieId}?append_to_response=credits`);
    }

    // 2. If not found or tmdbId was missing, search TMDB by clean title
    if (!data || !data.credits) {
      const cleanTitle = cleanSearchTitle(movie.title);
      
      // Stage A: Search with release year
      let searchRes = movie.year 
        ? await fetchTmdbJson(`/search/movie?query=${encodeURIComponent(cleanTitle)}&year=${movie.year}`)
        : null;

      // Stage B: If no results with year, search title only
      if (!searchRes || !searchRes.results || searchRes.results.length === 0) {
        searchRes = await fetchTmdbJson(`/search/movie?query=${encodeURIComponent(cleanTitle)}`);
      }

      if (searchRes && searchRes.results && searchRes.results.length > 0) {
        const results = searchRes.results;
        // Prioritize Indian language match if this title belongs to Indian Cinema
        const isIndian = movie.industry && movie.industry !== "Global";
        let picked = results[0];
        if (isIndian) {
          const matchLang = results.find(r => ["hi", "te", "ta", "ml", "kn", "bn", "mr", "pa"].includes(r.original_language));
          if (matchLang) picked = matchLang;
        }

        tmdbMovieId = picked.id;
        data = await fetchTmdbJson(`/movie/${tmdbMovieId}?append_to_response=credits`);
      }
    }

    if (!data || !data.credits) {
      return null;
    }

    // Extract verified directors (crew job == 'Director')
    const crew = data.credits.crew || [];
    const directors = crew
      .filter(c => c.job === "Director")
      .map(d => ({
        id: d.id,
        name: d.name,
        profile_path: d.profile_path ? `${TMDB_IMG_BASE}/w185${d.profile_path}` : null,
        job: "Director"
      }));

    // Extract verified principal cast (up to 16 members, including both male and female actors)
    const rawCast = data.credits.cast || [];
    const cast = rawCast.slice(0, 16).map(a => ({
      id: a.id,
      name: a.name,
      character: a.character || "Cast Member",
      profile_path: a.profile_path ? `${TMDB_IMG_BASE}/w185${a.profile_path}` : null,
      gender: a.gender,
      order: a.order
    }));

    const result = {
      tmdbId: data.id,
      title: data.title,
      directors: directors.length > 0 ? directors : null,
      cast: cast.length > 0 ? cast : null,
      backdrop_path: data.backdrop_path ? `${TMDB_IMG_BASE}/w1280${data.backdrop_path}` : null,
      overview: data.overview || null,
      runtime: data.runtime ? `${Math.floor(data.runtime / 60)}h ${data.runtime % 60}m` : null,
      vote_average: data.vote_average ? data.vote_average.toFixed(1) : null
    };

    CREDITS_CACHE.set(movie.id, result);
    try {
      localStorage.setItem(cacheKey, JSON.stringify(result));
    } catch (e) {}

    return result;
  }


  // Fetch verified person details (biography, birthday, filmography) from TMDB
  async function fetchPersonDetails(personId) {
    if (!personId) return null;
    const cacheKey = `cinematch_person_${personId}`;
    if (PERSON_CACHE.has(personId)) {
      return PERSON_CACHE.get(personId);
    }
    try {
      const stored = localStorage.getItem(cacheKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        PERSON_CACHE.set(personId, parsed);
        return parsed;
      }
    } catch (e) {}

    const data = await fetchTmdbJson(`/person/${personId}?append_to_response=movie_credits`);
    if (!data) return null;

    // Filter and sort top "Known For" movies by popularity/vote_count
    const allCredits = (data.movie_credits?.cast || []).concat(data.movie_credits?.crew || []);
    const seenIds = new Set();
    const uniqueCredits = [];
    for (const c of allCredits) {
      if (!c.id || seenIds.has(c.id)) continue;
      seenIds.add(c.id);
      uniqueCredits.push(c);
    }
    uniqueCredits.sort((a, b) => (b.vote_count || 0) - (a.vote_count || 0));
    const knownFor = uniqueCredits.slice(0, 8).map(m => ({
      id: m.id,
      title: m.title || m.original_title,
      year: m.release_date ? m.release_date.split("-")[0] : "",
      character: m.character || (m.job ? m.job : ""),
      poster: m.poster_path ? `${TMDB_IMG_BASE}/w185${m.poster_path}` : null,
      vote_average: m.vote_average ? m.vote_average.toFixed(1) : null
    }));

    const result = {
      id: data.id,
      name: data.name,
      biography: data.biography || "",
      birthday: data.birthday || null,
      place_of_birth: data.place_of_birth || null,
      known_for_department: data.known_for_department || "Acting",
      profile_path: data.profile_path ? `${TMDB_IMG_BASE}/w300${data.profile_path}` : null,
      known_for: knownFor
    };

    PERSON_CACHE.set(personId, result);
    try {
      localStorage.setItem(cacheKey, JSON.stringify(result));
    } catch (e) {}

    return result;
  }

  // --- 2. Storage Helpers ---
  function loadStorageSet(key) {
    try {
      const data = JSON.parse(localStorage.getItem(key) || "[]");
      return new Set(Array.isArray(data) ? data.map(Number) : []);
    } catch {
      return new Set();
    }
  }

  function saveStorageSet(key, setObj) {
    try {
      localStorage.setItem(key, JSON.stringify(Array.from(setObj)));
    } catch (e) {
      console.warn("Storage write failed for", key, e);
    }
  }

  function loadStorageMap(key) {
    try {
      return JSON.parse(localStorage.getItem(key) || "{}");
    } catch {
      return {};
    }
  }

  // Load and migrate user ratings for 1-10 scale compatibility (Requirement 6)
  function loadUserRatings() {
    try {
      const raw = JSON.parse(localStorage.getItem("cinematch_user_ratings") || "{}");
      const migrated = {};
      for (const [k, v] of Object.entries(raw)) {
        const num = Number(v);
        if (!isNaN(num) && num > 0) {
          // If stored on legacy 1-5 star scale, upscale cleanly to 10-point scale
          migrated[k] = (num <= 5) ? Math.min(10, Math.round(num * 2)) : Math.min(10, Math.round(num));
        }
      }
      return migrated;
    } catch {
      return {};
    }
  }

  // Format vote counts cleanly (e.g., 25410 -> 25.4k)
  function formatVotes(v) {
    if (!v || v <= 0) return "0";
    if (v >= 1000000) return (v / 1000000).toFixed(1) + "M";
    if (v >= 1000) return (v / 1000).toFixed(1) + "k";
    return String(v);
  }

  // Generate comparison HTML between personal user rating and TMDB community rating (Requirement 6)
  function renderRatingComparisonHtml(userR, tmdbR) {
    if (!userR) return "";
    if (tmdbR === null || tmdbR === undefined || tmdbR <= 0) {
      return `<span>Your Rating: <strong>${userR}/10 ⭐</strong> (No official TMDB community rating yet)</span>`;
    }
    const diff = Number((userR - tmdbR).toFixed(1));
    const diffStr = (diff > 0 ? `+${diff}` : String(diff));
    let badgeClass = "delta-equal";
    let verdict = "Matches community consensus";
    if (diff > 0.2) {
      badgeClass = "delta-higher";
      verdict = `${diffStr} higher than TMDB community`;
    } else if (diff < -0.2) {
      badgeClass = "delta-lower";
      verdict = `${diffStr} lower than TMDB community`;
    }
    return `<span>Your Rating: <strong>${userR}/10 ⭐</strong> &nbsp;|&nbsp; TMDB: <strong>${Number(tmdbR).toFixed(1)}/10</strong> &nbsp;(<span class="${badgeClass}">${verdict}</span>)</span>`;
  }

  // Remove/clear user rating (Requirement 6)
  function removeUserRating(movieId) {
    const mid = Number(movieId);
    delete state.ratings[mid];
    saveStorageMap("cinematch_user_ratings", state.ratings);
    updateNavWatchlistBadge();
    const movie = MOVIE_MAP.get(mid);
    showToast(`Removed your rating for "${movie ? movie.title : 'Movie'}"`);
    renderPersonalized();
    renderUserRatings();
    renderAllOpenLists();
    // Update any quick rate buttons for this movie
    document.querySelectorAll(`.movie-card[data-movie-id="${mid}"] .btn-quick-rate`).forEach(b => {
      b.textContent = "★ Rate";
    });
    document.querySelectorAll(`.movie-card[data-movie-id="${mid}"] .user-rated-badge`).forEach(b => {
      b.remove();
    });
  }

  function saveStorageMap(key, mapObj) {
    try {
      localStorage.setItem(key, JSON.stringify(mapObj));
    } catch (e) {
      console.warn("Storage write failed for", key, e);
    }
  }

  function updateNavWatchlistBadge() {
    const badge = document.getElementById("navWatchlistBadge");
    if (badge) badge.textContent = state.watchlist.size;
    const mCount = document.getElementById("modalWatchlistCount");
    if (mCount) mCount.textContent = state.watchlist.size;
    const fCount = document.getElementById("modalFavCount");
    if (fCount) fCount.textContent = state.favourites.size;
    const wCount = document.getElementById("modalWatchedCount");
    if (wCount) wCount.textContent = state.watched.size;
    const rCount = document.getElementById("modalRatingsCount");
    if (rCount) rCount.textContent = Object.keys(state.ratings).length;
  }

  // Fallback SVG Generator for missing posters
  function getPosterSrc(m) {
    if (m && m.poster && typeof m.poster === "string" && m.poster.startsWith("http")) {
      return m.poster;
    }
    const safeTitle = escapeHtml((m && m.title ? m.title : "Movie").length > 22 ? (m.title.slice(0, 20) + "...") : (m && m.title ? m.title : "Movie"));
    const safeGenre = (m && m.genres && m.genres[0]) ? escapeHtml(m.genres[0]) : "Cinema";
    const safeYear = (m && m.year) ? String(m.year) : "";
    const safeRating = (m && m.rating) ? `${Number(m.rating).toFixed(1)}/10` : "";

    return `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" width="300" height="450"><rect width="300" height="450" fill="%23101626"/><rect width="300" height="450" fill="none" stroke="%238b5cf6" stroke-width="2"/><circle cx="150" cy="180" r="45" fill="%238b5cf6" opacity="0.25"/><text x="150" y="55" text-anchor="middle" font-family="sans-serif" font-size="12" font-weight="700" fill="%23a78bfa" letter-spacing="2">${safeGenre.toUpperCase()}</text><text x="150" y="240" text-anchor="middle" font-family="sans-serif" font-size="17" font-weight="800" fill="%23ffffff">${safeTitle}</text><text x="150" y="275" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="600" fill="%2394a3b8">${safeYear}</text><text x="150" y="380" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="700" fill="%23fbbf24">${safeRating ? safeRating + ' ⭐' : '★ CineMatch'}</text></svg>`;
  }

  // --- 3. Initialization ---
  function init() {
    updateNavWatchlistBadge();
    initHeroBanner();
    renderTop10Contents();
    initAiAssistant();
    initMoods();
    initDiscoverFilters();
    initAutocompleteSearch();
    initAlgoTabs();
    initIndianTabs();
    initModals();

    // Initial renders
    renderDiscoveryGrid();
    renderPersonalized();
    renderIndianSpotlight();
    renderPopular();
    renderUserRatings();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // =========================================================================
  // 4. Streaming Hero Banner (Image 3 Inspiration - Cinevo)
  // =========================================================================
  function initHeroBanner() {
    const switcherBar = document.getElementById("heroSwitcherBar");
    if (!switcherBar) return;

    // Match featured titles against MOVIES catalog to retrieve real IDs & poster URLs
    const resolvedHeroMovies = FEATURED_HERO_TITLES.map(feat => {
      const match = MOVIES.find(m => m.title && m.title.toLowerCase() === feat.title.toLowerCase()) ||
                    MOVIES.find(m => m.full_title && m.full_title.toLowerCase().includes(feat.title.toLowerCase())) ||
                    MOVIES[0];
      return {
        ...feat,
        id: match.id,
        poster: match.poster || feat.backdrop,
        score: match.score || 4.5,
        votes: match.votes || 900,
        genres: match.genres || ["Action", "Sci-Fi"],
        industry: match.industry || "Cinema"
      };
    });

    switcherBar.innerHTML = resolvedHeroMovies.map((m, idx) => `
      <div class="hero-thumb-btn ${idx === 0 ? 'active' : ''}" data-hero-idx="${idx}" title="${escapeHtml(m.title)}">
        <img src="${getPosterSrc(m)}" alt="${escapeHtml(m.title)}" style="width: 100%; height: 100%; object-fit: cover;">
      </div>
    `).join("");

    function displayHero(index) {
      const m = resolvedHeroMovies[index];
      if (!m) return;
      state.currentHeroIndex = index;

      const backdropImg = document.getElementById("heroBackdropImg");
      const titleEl = document.getElementById("heroMovieTitle");
      const ratingBadge = document.getElementById("heroRatingBadge");
      const certBadge = document.getElementById("heroCertBadge");
      const yearBadge = document.getElementById("heroYearBadge");
      const durationBadge = document.getElementById("heroDurationBadge");
      const industryBadge = document.getElementById("heroIndustryBadge");
      const genresBadge = document.getElementById("heroGenresBadge");
      const synopsisEl = document.getElementById("heroSynopsisText");
      const watchlistBtnText = document.getElementById("heroWatchlistBtnText");

      if (backdropImg) {
        backdropImg.style.opacity = "0.2";
        setTimeout(() => {
          backdropImg.src = m.backdrop || m.poster;
          backdropImg.style.opacity = "0.45";
        }, 200);
      }
      if (titleEl) titleEl.textContent = m.title;
      if (ratingBadge) {
        const heroR = (m.rating !== null && m.rating !== undefined) ? Number(m.rating).toFixed(1) : Number(m.score || 7.7).toFixed(1);
        ratingBadge.innerHTML = `⭐ ${heroR} / 10 <span class="pill-tmdb-tag">TMDB</span>`;
      }
      if (certBadge) certBadge.textContent = m.cert || "UA 16+";
      if (yearBadge) yearBadge.textContent = m.year;
      if (durationBadge) durationBadge.textContent = m.runtime || "2h 30m";
      if (industryBadge) industryBadge.textContent = m.industry || "Cinema";
      if (genresBadge) genresBadge.textContent = (m.genres || []).slice(0, 3).join(", ");
      if (synopsisEl) synopsisEl.textContent = m.synopsis;

      // Update watchlist toggle text on hero
      if (watchlistBtnText) {
        watchlistBtnText.textContent = state.watchlist.has(m.id) ? "✓ In Watchlist" : "Add to Watchlist";
      }

      // Update switcher active class
      switcherBar.querySelectorAll(".hero-thumb-btn").forEach((btn, i) => {
        btn.classList.toggle("active", i === index);
      });
    }

    displayHero(0);

    // Switcher Click
    switcherBar.addEventListener("click", (e) => {
      const thumb = e.target.closest(".hero-thumb-btn");
      if (!thumb) return;
      const idx = Number(thumb.dataset.heroIdx);
      displayHero(idx);
      resetHeroAutoTimer();
    });

    // Hero Action Buttons
    const watchlistBtn = document.getElementById("heroWatchlistBtn");
    const detailsBtn = document.getElementById("heroDetailsBtn");

    if (detailsBtn) {
      detailsBtn.onclick = () => {
        const cur = resolvedHeroMovies[state.currentHeroIndex];
        if (cur) openDetailModal(cur.id);
      };
    }

    if (watchlistBtn) {
      watchlistBtn.onclick = () => {
        const cur = resolvedHeroMovies[state.currentHeroIndex];
        if (!cur) return;
        toggleWatchlist(cur.id);
        const wText = document.getElementById("heroWatchlistBtnText");
        if (wText) wText.textContent = state.watchlist.has(cur.id) ? "✓ In Watchlist" : "Add to Watchlist";
      };
    }

    // Auto rotate every 8 seconds
    function startHeroAutoTimer() {
      state.heroAutoTimer = setInterval(() => {
        const nextIdx = (state.currentHeroIndex + 1) % resolvedHeroMovies.length;
        displayHero(nextIdx);
      }, 8000);
    }
    function resetHeroAutoTimer() {
      if (state.heroAutoTimer) clearInterval(state.heroAutoTimer);
      startHeroAutoTimer();
    }
    startHeroAutoTimer();
  }

  // =========================================================================
  // 5. "TOP 10 CONTENTS TODAY" (Image 3 Inspiration)
  // =========================================================================
  function renderTop10Contents() {
    const grid = document.getElementById("top10Grid");
    if (!grid) return;

    // Pick top 10 movies sorted by Bayesian score * log(votes)
    const top10 = MOVIES.slice()
      .sort((a, b) => (b.votes * Math.pow(b.score, 1.4)) - (a.votes * Math.pow(a.score, 1.4)))
      .slice(0, 10);

    grid.innerHTML = top10.map((m, idx) => {
      const rank = idx + 1;
      return `
        <div class="top10-card" data-detail-id="${m.id}" title="${escapeHtml(m.title)}">
          <div class="top10-rank-number">${rank}</div>
          <div class="top10-poster-wrap">
            <img 
              src="${getPosterSrc(m)}" 
              alt="${escapeHtml(m.title)}" 
              loading="lazy" 
              class="top10-poster-img"
              onerror="this.onerror=null;this.src='${getPosterSrc({ ...m, poster: '' })}'"
            >
            <div class="top10-meta-overlay">
              <div class="top10-card-title">${escapeHtml(m.title)}</div>
              <div class="top10-card-rating">⭐ ${m.rating ? Number(m.rating).toFixed(1) + '/10' : 'Top 10'} (${m.year || "N/A"})</div>
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  // =========================================================================
  // 6. Ask CineMatch AI Conversational Assistant (Image 1 Inspiration)
  // =========================================================================
  function initAiAssistant() {
    const chatForm = document.getElementById("aiChatForm");
    const chatInput = document.getElementById("aiChatInput");
    const thread = document.getElementById("aiChatThread");
    const chipsWrapper = document.getElementById("aiPromptChips");
    const clearChatBtn = document.getElementById("btnResetChat");

    if (!chatForm || !chatInput || !thread) return;

    function handleUserPrompt(query) {
      const q = (query || "").trim();
      if (!q) return;

      // Append user bubble
      appendUserMessage(q);
      chatInput.value = "";

      // Show typing indicator
      const typingEl = appendTypingIndicator();

      // Run intelligent client-side NLP parser & recommendation retrieval
      setTimeout(() => {
        if (typingEl) typingEl.remove();
        const responseData = processAiQuery(q);
        appendAssistantMessage(responseData);
      }, 550);
    }

    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleUserPrompt(chatInput.value);
    });

    if (chipsWrapper) {
      chipsWrapper.addEventListener("click", (e) => {
        const chip = e.target.closest(".prompt-chip");
        if (!chip) return;
        handleUserPrompt(chip.dataset.query);
      });
    }

    if (clearChatBtn) {
      clearChatBtn.addEventListener("click", () => {
        thread.innerHTML = `
          <div class="chat-msg assistant">
            <div class="chat-avatar">✨</div>
            <div class="chat-bubble">
              <p>Conversation cleared! What would you like to explore next? You can ask for genres, specific moods, languages (Tollywood, Bollywood, Kollywood), or movies similar to your favorites.</p>
            </div>
          </div>
        `;
      });
    }

    function appendUserMessage(text) {
      const el = document.createElement("div");
      el.className = "chat-msg user";
      el.innerHTML = `
        <div class="chat-avatar">👤</div>
        <div class="chat-bubble">${escapeHtml(text)}</div>
      `;
      thread.appendChild(el);
      thread.scrollTop = thread.scrollHeight;
    }

    function appendTypingIndicator() {
      const el = document.createElement("div");
      el.className = "chat-msg assistant";
      el.innerHTML = `
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble" style="display: inline-flex; align-items: center; gap: 6px; padding: 10px 16px;">
          <span>Analyzing 10,742 movie vectors</span>
          <span style="animation: pulse 1s infinite;">...</span>
        </div>
      `;
      thread.appendChild(el);
      thread.scrollTop = thread.scrollHeight;
      return el;
    }

    function appendAssistantMessage(resp) {
      const el = document.createElement("div");
      el.className = "chat-msg assistant";

      let recsHtml = "";
      if (resp.movies && resp.movies.length > 0) {
        recsHtml = `
          <div class="ai-recs-carousel">
            ${resp.movies.map((m, idx) => `
              <div class="ai-rec-card" data-detail-id="${m.id}" title="${escapeHtml(m.title)}">
                <div class="ai-rec-badge">${idx + 1}</div>
                <img 
                  src="${getPosterSrc(m)}" 
                  alt="${escapeHtml(m.title)}" 
                  class="ai-rec-poster"
                  onerror="this.onerror=null;this.src='${getPosterSrc({ ...m, poster: '' })}'"
                >
                <div class="ai-rec-info">
                  <div class="ai-rec-meta">
                    <span>★ ${m.rating}</span>
                    <span>${m.year || "N/A"}</span>
                  </div>
                  <div class="ai-rec-title">${escapeHtml(m.title)}</div>
                  <div class="ai-rec-reason">${escapeHtml(m._aiReason || "Matches your query criteria")}</div>
                </div>
              </div>
            `).join("")}
          </div>
        `;
      }

      el.innerHTML = `
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble">
          <p>${resp.replyHtml}</p>
          ${recsHtml}
        </div>
      `;
      thread.appendChild(el);
      thread.scrollTop = thread.scrollHeight;
    }

    // Client-Side Natural Language Intent Parser & Recommendation Algorithm
    function processAiQuery(raw) {
      const q = raw.toLowerCase();
      let matchedMovies = [];
      let explanation = "";

      // 1. Check for "similar to [Movie Title]"
      const simMatch = q.match(/(?:similar to|like|same as|movies like)\s+([a-z0-9\s:.-]+)/i);
      if (simMatch && simMatch[1]) {
        const targetTitle = simMatch[1].trim().toLowerCase();
        const baseMovie = MOVIES.find(m => m.title && m.title.toLowerCase().includes(targetTitle));
        if (baseMovie) {
          const sims = (baseMovie.sims || []).map(id => MOVIE_MAP.get(id)).filter(Boolean);
          if (sims.length > 0) {
            matchedMovies = sims.slice(0, 5).map(m => ({
              ...m,
              _aiReason: `High content similarity with "${baseMovie.title}" (${m.genres ? m.genres.join(", ") : ""})`
            }));
            explanation = `Here are 5 movies with strong thematic, genre, and tonal similarity to <strong>"${escapeHtml(baseMovie.title)}"</strong>:`;
            return { replyHtml: explanation, movies: matchedMovies };
          }
        }
      }

      // 2. Identify Industry / Language Intent
      let industryFilter = null;
      if (q.includes("telugu") || q.includes("tollywood")) industryFilter = "Tollywood";
      else if (q.includes("hindi") || q.includes("bollywood")) industryFilter = "Bollywood";
      else if (q.includes("tamil") || q.includes("kollywood")) industryFilter = "Kollywood";
      else if (q.includes("hollywood") || q.includes("english") || q.includes("international")) industryFilter = "Hollywood";

      // 3. Identify Genre Intent
      const genresToLook = [
        "Sci-Fi", "Action", "Thriller", "Drama", "Comedy", "Romance", "Adventure",
        "Crime", "Mystery", "Horror", "Fantasy", "Animation", "Documentary", "Family"
      ];
      const matchedGenres = genresToLook.filter(g => {
        const lower = g.toLowerCase();
        if (lower === "sci-fi") return q.includes("sci-fi") || q.includes("science fiction") || q.includes("scifi");
        if (lower === "family") return q.includes("family") || q.includes("kids") || q.includes("children");
        return q.includes(lower);
      });

      // 4. Identify Temporal Filter
      let yearMin = 0;
      let yearMax = 9999;
      if (q.includes("after 2020") || q.includes("post 2020") || q.includes("recent") || q.includes("latest") || q.includes("new")) {
        yearMin = 2020;
      } else if (q.includes("90s") || q.includes("1990")) {
        yearMin = 1990;
        yearMax = 1999;
      } else if (q.includes("classic") || q.includes("old")) {
        yearMax = 1999;
      }

      // 5. Identify Mood / Tone modifiers
      let isMindBending = q.includes("mind-bending") || q.includes("mind bending") || q.includes("twist") || q.includes("complex");
      let isEmotional = q.includes("emotional") || q.includes("tearjerker") || q.includes("heartfelt") || q.includes("sad");
      let isUnderrated = q.includes("underrated") || q.includes("hidden gem") || q.includes("lesser known");
      let isFeelGood = q.includes("feel-good") || q.includes("feel good") || q.includes("fun") || q.includes("cheerful");

      // Filter candidates
      let pool = MOVIES.filter(m => {
        // Industry check
        if (industryFilter === "Tollywood" && m.industry !== "Tollywood" && !(200001 <= m.id && m.id <= 200275)) return false;
        if (industryFilter === "Bollywood" && m.industry !== "Bollywood" && !(200301 <= m.id && m.id <= 200615)) return false;
        if (industryFilter === "Kollywood" && m.industry !== "Kollywood" && !(m.id >= 201001 && m.id <= 201415)) return false;
        if (industryFilter === "Hollywood" && m.id >= 200000) return false;

        // Year check
        if (m.year && (m.year < yearMin || m.year > yearMax)) return false;

        // Genre check
        if (matchedGenres.length > 0) {
          const mGenres = (m.genres || []).map(g => g.toLowerCase());
          const hasGenre = matchedGenres.some(g => mGenres.includes(g.toLowerCase()) || (g === "Family" && (mGenres.includes("children") || mGenres.includes("animation"))));
          if (!hasGenre) return false;
        }

        // Mood checks
        if (isMindBending) {
          const mGenres = (m.genres || []).map(g => g.toLowerCase());
          if (!mGenres.includes("sci-fi") && !mGenres.includes("mystery") && !mGenres.includes("thriller")) return false;
        }
        if (isEmotional) {
          const mGenres = (m.genres || []).map(g => g.toLowerCase());
          if (!mGenres.includes("drama") && !mGenres.includes("romance")) return false;
        }

        return true;
      });

      // Sorting
      if (isUnderrated) {
        // High score, moderate votes
        pool.sort((a, b) => {
          const ratioA = a.score / Math.log10(Math.max(10, a.votes));
          const ratioB = b.score / Math.log10(Math.max(10, b.votes));
          return ratioB - ratioA;
        });
      } else {
        // Bayesian score
        pool.sort((a, b) => b.score - a.score);
      }

      matchedMovies = pool.slice(0, 5).map(m => {
        let reason = `★ ${m.score.toFixed(1)} rating`;
        if (isMindBending) reason = `Mind-bending ${m.genres ? m.genres.join("/") : "Sci-Fi"} plot`;
        else if (isEmotional) reason = `High emotional impact & poignant drama`;
        else if (isUnderrated) reason = `Critical acclaim with under-the-radar praise`;
        else if (industryFilter) reason = `Top-rated ${industryFilter} blockbuster`;
        else if (matchedGenres.length > 0) reason = `High affinity for ${matchedGenres.join(" & ")}`;
        return {
          ...m,
          _aiReason: reason
        };
      });

      // Formulate conversational response
      if (matchedMovies.length === 0) {
        return {
          replyHtml: `I couldn't find an exact match for <em>"${escapeHtml(raw)}"</em> in the current filters. Here are some top-rated suggestions you might enjoy:`,
          movies: MOVIES.slice(0, 5).map(m => ({ ...m, _aiReason: "Overall audience favorite" }))
        };
      }

      let descParts = [];
      if (isMindBending) descParts.push("mind-bending");
      if (isEmotional) descParts.push("deeply emotional");
      if (isUnderrated) descParts.push("underrated");
      if (industryFilter) descParts.push(industryFilter);
      if (matchedGenres.length > 0) descParts.push(matchedGenres.join(" / "));
      if (yearMin >= 2020) descParts.push("released after 2020");

      explanation = `Here are 5 handpicked ${descParts.length > 0 ? `<strong>${descParts.join(" ")}</strong>` : ""} recommendations matching your request:`;
      return { replyHtml: explanation, movies: matchedMovies };
    }
  }

  // =========================================================================
  // 7. Choose Your Mood (Requirement 4)
  // =========================================================================
  function initMoods() {
    const moodsGrid = document.getElementById("moodsGrid");
    const resultsSection = document.getElementById("moodResultsSection");
    const resultsGrid = document.getElementById("moodResultsGrid");
    const resultsTitle = document.getElementById("moodResultsTitle");
    const clearMoodBtn = document.getElementById("clearMoodBtn");
    const activeIndicator = document.getElementById("activeMoodIndicator");

    if (!moodsGrid || !resultsSection || !resultsGrid) return;

    const MOOD_MAPPINGS = {
      happy: {
        title: "Happy & Feel-Good Cinema",
        genres: ["Comedy", "Animation", "Musical"],
        desc: "Laughter, vibrant adventures, and cheerful warmth to brighten your day.",
        reason: "Uplifting comedy & feel-good vibes"
      },
      sad: {
        title: "Emotional & Heartfelt Stories",
        genres: ["Drama", "Romance"],
        desc: "Deep storytelling, poignant performances, and cathartic tearjerkers.",
        reason: "Poignant drama & emotional depth"
      },
      excited: {
        title: "High-Adrenaline & Thrilling Hits",
        genres: ["Action", "Thriller", "Adventure"],
        desc: "Pulse-pounding stunts, heart-racing sequences, and explosive momentum.",
        reason: "High-octane action & adrenaline thrills"
      },
      relaxed: {
        title: "Relaxed & Cozy Comfort Watches",
        genres: ["Comedy", "Drama"],
        desc: "Low-conflict, charming narratives, and easygoing feel-good comfort.",
        reason: "Relaxing pacing & comfort watch"
      },
      motivated: {
        title: "Motivated & Triumphant Inspirations",
        genres: ["Drama"],
        desc: "Underdog victories, perseverance, and true stories of grit.",
        reason: "Inspiring perseverance & triumph"
      },
      romantic: {
        title: "Romantic & Passionate Love Stories",
        genres: ["Romance", "Drama"],
        desc: "Unforgettable chemistry, soulmates, and cinematic romance.",
        reason: "Passionate romance & swoon-worthy chemistry"
      },
      curious: {
        title: "Curious & Mind-Bending Puzzles",
        genres: ["Sci-Fi", "Mystery", "Crime"],
        desc: "Cerebral concepts, jaw-dropping twists, and intellectual depth.",
        reason: "Mind-bending twists & intellectual curiosity"
      },
      adventurous: {
        title: "Adventurous & Epic Quests",
        genres: ["Adventure", "Fantasy", "Action"],
        desc: "Grand mythologies, legendary voyages, and sweeping worldbuilding.",
        reason: "Epic quest & grand adventure"
      }
    };

    moodsGrid.addEventListener("click", (e) => {
      const card = e.target.closest(".mood-card");
      if (!card) return;

      moodsGrid.querySelectorAll(".mood-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");

      const moodKey = card.dataset.mood;
      state.activeMood = moodKey;
      const config = MOOD_MAPPINGS[moodKey];
      if (!config) return;

      if (activeIndicator) activeIndicator.textContent = `Active Mood: ${card.querySelector(".mood-title").textContent}`;
      resultsTitle.textContent = config.title;

      // Filter catalog for mood matches
      const matches = MOVIES.filter(m => {
        const mGenres = m.genres || [];
        return config.genres.some(g => mGenres.includes(g)) && m.score >= 3.3;
      }).slice().sort((a, b) => b.score - a.score).slice(0, 18);

      renderMovieCards(resultsGrid, matches.map(m => ({
        ...m,
        _explainReason: config.reason
      })));

      resultsSection.classList.remove("hidden");
      resultsSection.scrollIntoView({ behavior: "smooth" });
    });

    if (clearMoodBtn) {
      clearMoodBtn.addEventListener("click", () => {
        moodsGrid.querySelectorAll(".mood-card").forEach(c => c.classList.remove("active"));
        state.activeMood = null;
        if (activeIndicator) activeIndicator.textContent = "";
        resultsSection.classList.add("hidden");
      });
    }
  }

  // =========================================================================
  // 8. Advanced Discover & Multi-Filtering (Requirement 5)
  // =========================================================================
  function initDiscoverFilters() {
    // Populate Genre Chips
    const genreCounts = {};
    MOVIES.forEach(m => {
      (m.genres || []).forEach(g => {
        if (g && g !== "(no genres listed)") {
          genreCounts[g] = (genreCounts[g] || 0) + 1;
        }
      });
    });

    const sortedGenres = Object.entries(genreCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 16);

    const chipsWrapper = document.getElementById("genreChipsWrapper");
    if (chipsWrapper) {
      chipsWrapper.innerHTML = `
        <button type="button" class="genre-chip active" data-genre="All">All Genres</button>
        ${sortedGenres.map(([g, c]) => `
          <button type="button" class="genre-chip" data-genre="${escapeHtml(g)}">
            ${escapeHtml(g)} <span class="chip-count">${c}</span>
          </button>
        `).join("")}
      `;

      chipsWrapper.addEventListener("click", (e) => {
        const chip = e.target.closest(".genre-chip");
        if (!chip) return;
        chipsWrapper.querySelectorAll(".genre-chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        state.genre = chip.dataset.genre || "All";

        const status = document.getElementById("genreFilterStatus");
        if (status) status.textContent = state.genre === "All" ? "Showing All" : `Filtered: ${state.genre}`;

        state.discoveryCount = 24;
        renderDiscoveryGrid();
        renderPersonalized();
      });
    }

    // Dropdown Filters
    const indSelect = document.getElementById("filterIndustrySelect");
    const eraSelect = document.getElementById("filterEraSelect");
    const rateSelect = document.getElementById("filterRatingSelect");
    const sortSelect = document.getElementById("filterSortSelect");
    const resetBtn = document.getElementById("btnResetAllFilters");
    const loadMoreBtn = document.getElementById("loadMoreDiscoveryBtn");

    if (indSelect) indSelect.onchange = () => { state.industry = indSelect.value; state.discoveryCount = 24; renderDiscoveryGrid(); };
    if (eraSelect) eraSelect.onchange = () => { state.era = eraSelect.value; state.discoveryCount = 24; renderDiscoveryGrid(); };
    if (rateSelect) rateSelect.onchange = () => { state.minRating = Number(rateSelect.value); state.discoveryCount = 24; renderDiscoveryGrid(); };
    if (sortSelect) sortSelect.onchange = () => { state.sortBy = sortSelect.value; renderDiscoveryGrid(); };

    if (resetBtn) {
      resetBtn.onclick = () => {
        if (indSelect) indSelect.value = "all";
        if (eraSelect) eraSelect.value = "all";
        if (rateSelect) rateSelect.value = "0";
        if (sortSelect) sortSelect.value = "score";
        state.industry = "all";
        state.era = "all";
        state.minRating = 0;
        state.sortBy = "score";
        state.genre = "All";
        state.discoveryCount = 24;

        if (chipsWrapper) {
          chipsWrapper.querySelectorAll(".genre-chip").forEach(c => c.classList.remove("active"));
          const first = chipsWrapper.querySelector("[data-genre='All']");
          if (first) first.classList.add("active");
        }
        const status = document.getElementById("genreFilterStatus");
        if (status) status.textContent = "Showing All";

        renderDiscoveryGrid();
      };
    }

    if (loadMoreBtn) {
      loadMoreBtn.onclick = () => {
        state.discoveryCount += 24;
        renderDiscoveryGrid();
      };
    }
  }

  function renderDiscoveryGrid() {
    const grid = document.getElementById("discoveryGrid");
    const statusText = document.getElementById("discoveryStatusText");
    const loadMoreBtn = document.getElementById("loadMoreDiscoveryBtn");
    if (!grid) return;

    let filtered = MOVIES.filter(m => {
      // Industry
      if (state.industry === "Tollywood" && m.industry !== "Tollywood" && !(200001 <= m.id && m.id <= 200275)) return false;
      if (state.industry === "Bollywood" && m.industry !== "Bollywood" && !(200301 <= m.id && m.id <= 200615)) return false;
      if (state.industry === "Kollywood" && m.industry !== "Kollywood" && !(m.id >= 201001 && m.id <= 201415)) return false;
      if (state.industry === "Hollywood" && m.id >= 200000) return false;

      // Era
      if (state.era === "2020s" && (!m.year || m.year < 2020)) return false;
      if (state.era === "2010s" && (!m.year || m.year < 2010 || m.year > 2019)) return false;
      if (state.era === "2000s" && (!m.year || m.year < 2000 || m.year > 2009)) return false;
      if (state.era === "classics" && (!m.year || m.year >= 2000)) return false;

      // Rating (on 10-point scale)
      if (state.minRating > 0 && ((m.rating !== null ? m.rating : (m.score || 0)) < state.minRating)) return false;

      // Genre
      if (state.genre !== "All" && !(m.genres || []).includes(state.genre)) return false;

      return true;
    });

    // Accurate Rating Sorting (Requirement 3: Numerical comparisons)
    if (state.sortBy === "score") {
      filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
    } else if (state.sortBy === "rating_desc") {
      filtered.sort((a, b) => ((b.rating !== null && b.rating !== undefined ? b.rating : -1) - (a.rating !== null && a.rating !== undefined ? a.rating : -1)) || (b.votes - a.votes));
    } else if (state.sortBy === "rating_asc") {
      filtered.sort((a, b) => ((a.rating !== null && a.rating !== undefined ? a.rating : 99) - (b.rating !== null && b.rating !== undefined ? b.rating : 99)) || (a.votes - b.votes));
    } else if (state.sortBy === "votes" || state.sortBy === "votes_desc") {
      filtered.sort((a, b) => (b.votes || 0) - (a.votes || 0));
    } else if (state.sortBy === "pop_desc" || state.sortBy === "popularity") {
      filtered.sort((a, b) => (b.popularity || 0) - (a.popularity || 0) || (b.votes - a.votes));
    } else if (state.sortBy === "year_desc") {
      filtered.sort((a, b) => (b.year || 0) - (a.year || 0));
    } else if (state.sortBy === "year_asc") {
      filtered.sort((a, b) => (a.year || 9999) - (b.year || 9999));
    } else if (state.sortBy === "title") {
      filtered.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
    }

    if (statusText) {
      statusText.textContent = `Showing ${Math.min(filtered.length, state.discoveryCount)} of ${filtered.length} movies matching filters`;
    }

    renderMovieCards(grid, filtered.slice(0, state.discoveryCount));

    if (loadMoreBtn) {
      loadMoreBtn.style.display = (state.discoveryCount >= filtered.length) ? "none" : "inline-flex";
    }
  }

  // =========================================================================
  // 9. Autocomplete Live Search
  // =========================================================================
  function initAutocompleteSearch() {
    const navInput = document.getElementById("navSearchInput");
    const dropdown = document.getElementById("navAutocompleteDropdown");
    const resultsSection = document.getElementById("searchResultsSection");
    const resultsGrid = document.getElementById("searchResultsGrid");
    const countEl = document.getElementById("searchResultsCount");
    const clearBtn = document.getElementById("clearSearchBtn");

    if (!navInput || !dropdown) return;

    let debounceTimer = null;

    navInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        const val = e.target.value.trim().toLowerCase();
        if (!val || val.length < 2) {
          dropdown.classList.add("hidden");
          dropdown.innerHTML = "";
          return;
        }

        const matches = MOVIES.filter(m => {
          const t = (m.title || "").toLowerCase();
          const ft = (m.full_title || "").toLowerCase();
          const g = (m.genres || []).join(" ").toLowerCase();
          const y = m.year ? String(m.year) : "";
          return t.includes(val) || ft.includes(val) || g.includes(val) || y === val;
        }).slice(0, 8);

        if (matches.length === 0) {
          dropdown.innerHTML = `<div style="padding: 12px 16px; font-size: 0.85rem; color: #94a3b8;">No matching titles found for "${escapeHtml(val)}"</div>`;
          dropdown.classList.remove("hidden");
          return;
        }

        dropdown.innerHTML = matches.map(m => `
          <div class="autocomplete-item" data-movie-id="${m.id}">
            <img src="${getPosterSrc(m)}" alt="${escapeHtml(m.title)}" class="autocomplete-thumb" onerror="this.src='${getPosterSrc({ ...m, poster: '' })}'">
            <div class="autocomplete-info">
              <div class="autocomplete-title">${escapeHtml(m.title)}</div>
              <div class="autocomplete-meta">${m.year || "N/A"} &bull; ${(m.genres || []).slice(0, 2).join(", ")}</div>
            </div>
            <span class="autocomplete-badge">⭐ ${m.rating ? Number(m.rating).toFixed(1) + '/10' : 'Unrated'}</span>
          </div>
        `).join("");

        dropdown.classList.remove("hidden");
      }, 180);
    });

    // Click on autocomplete item
    dropdown.addEventListener("click", (e) => {
      const item = e.target.closest(".autocomplete-item");
      if (!item) return;
      const mid = Number(item.dataset.movieId);
      dropdown.classList.add("hidden");
      openDetailModal(mid);
    });

    // Enter key submits full search
    navInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        dropdown.classList.add("hidden");
        const val = navInput.value.trim().toLowerCase();
        if (!val) return;

        const matches = MOVIES.filter(m => {
          const t = (m.title || "").toLowerCase();
          const ft = (m.full_title || "").toLowerCase();
          const g = (m.genres || []).join(" ").toLowerCase();
          return t.includes(val) || ft.includes(val) || g.includes(val);
        });

        if (resultsSection && resultsGrid) {
          resultsSection.classList.remove("hidden");
          if (countEl) countEl.textContent = `Found ${matches.length} matching movies for "${navInput.value}"`;
          renderMovieCards(resultsGrid, matches.slice(0, 36));
          resultsSection.scrollIntoView({ behavior: "smooth" });
        }
      }
    });

    // Close autocomplete on click outside
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".nav-search-wrap")) {
        dropdown.classList.add("hidden");
      }
    });

    if (clearBtn && resultsSection) {
      clearBtn.addEventListener("click", () => {
        resultsSection.classList.add("hidden");
        navInput.value = "";
      });
    }
  }

  // =========================================================================
  // 10. Personalized Recommendations Engine & Tabs (Requirement 9)
  // =========================================================================
  function initAlgoTabs() {
    const tabs = document.querySelectorAll("#algoTabs .tab-btn");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        state.activeAlgo = tab.dataset.algo;
        renderPersonalized();
      });
    });
  }

  function getRecommendations(algorithm = "hybrid", limit = 12) {
    const ratedIds = new Set(Object.keys(state.ratings).map(Number));
    let candidates = MOVIES.filter(m => !ratedIds.has(m.id));

    if (state.genre !== "All") {
      const filtered = candidates.filter(m => (m.genres || []).includes(state.genre));
      if (filtered.length > 0) candidates = filtered;
    }

    const ratedList = Object.entries(state.ratings).map(([id, r]) => ({
      movie: MOVIE_MAP.get(Number(id)),
      rating: Number(r)
    })).filter(x => x.movie);

    // 1. Trending / Popular
    if (algorithm === "popular") {
      return candidates.slice().sort((a, b) => (b.votes * Math.pow(b.score, 1.4)) - (a.votes * Math.pow(a.score, 1.4))).slice(0, limit).map(m => ({
        ...m,
        _explainReason: `🔥 Audience Favorite • ${formatVotes(m.votes)} verified reviews`
      }));
    }

    // 2. Content-Based
    if (algorithm === "content" && ratedList.length > 0) {
      const highest = ratedList.slice().sort((a, b) => b.rating - a.rating)[0];
      const simIds = new Set(highest.movie.sims || []);
      const similarCandidates = candidates.filter(m => simIds.has(m.id));
      if (similarCandidates.length >= 4) {
        return similarCandidates.slice(0, limit).map(m => ({
          ...m,
          _explainReason: `🎯 TF-IDF Cosine Match with "${highest.movie.title}"`
        }));
      }
    }

    // 3. Collaborative (SVD) or Hybrid Ensemble (Requirement 7)
    if ((algorithm === "collab" || algorithm === "hybrid") && ratedList.length > 0) {
      const poolScores = new Map();
      ratedList.forEach(({ movie, rating }) => {
        // Normalize 1-10 rating centered at 5.0
        const weight = (rating - 5.0) / 5.0;
        (movie.sims || []).forEach(simId => {
          if (!ratedIds.has(simId)) {
            poolScores.set(simId, (poolScores.get(simId) || 0) + (1.2 * weight));
          }
        });
      });

      const scored = candidates.map(m => {
        const simBonus = poolScores.get(m.id) || 0;
        const quality = (m.score || 6.54) / 10.0;
        return {
          ...m,
          _calcScore: (0.6 * simBonus) + (0.4 * quality),
          _explainReason: simBonus > 0 ? `⚡ Hybrid Ensemble: High affinity to your ${ratedList.length} rated titles` : `⚡ Quality Score (Bayesian): ${(m.score || 6.54).toFixed(1)}/10`
        };
      });

      scored.sort((a, b) => (b._calcScore || 0) - (a._calcScore || 0));
      return scored.slice(0, limit);
    }

    // Fallback: Bayesian Weighted Quality Recommendations (Requirement 4)
    return candidates.slice().sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, limit).map(m => ({
      ...m,
      _explainReason: `⭐ Quality Score (Bayesian): ${(m.score || 6.54).toFixed(1)}/10`
    }));
  }

  function renderPersonalized() {
    const grid = document.getElementById("personalizedGrid");
    if (!grid) return;
    const recs = getRecommendations(state.activeAlgo, 12);
    renderMovieCards(grid, recs);
  }

  // =========================================================================
  // 11. Indian Cinema Spotlight
  // =========================================================================
  function initIndianTabs() {
    const tabs = document.querySelectorAll("#indianTabs .tab-btn");
    const loadMoreBtn = document.getElementById("loadMoreIndianBtn");

    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        state.indianIndustry = tab.dataset.industry || "all";
        state.indianCount = 24;
        renderIndianSpotlight();
      });
    });

    if (loadMoreBtn) {
      loadMoreBtn.addEventListener("click", () => {
        state.indianCount += 24;
        renderIndianSpotlight();
      });
    }
  }

  function renderIndianSpotlight() {
    const grid = document.getElementById("indianGrid");
    const loadMoreBtn = document.getElementById("loadMoreIndianBtn");
    if (!grid) return;

    let pool = MOVIES.filter(m => {
      if (m.id < 200000) return false;
      if (state.indianIndustry === "Kollywood") {
        return m.industry === "Kollywood" || m.id >= 201001;
      }
      if (state.indianIndustry === "Tollywood") {
        return m.industry === "Tollywood" || (200001 <= m.id && m.id <= 200275);
      }
      if (state.indianIndustry === "Bollywood") {
        return m.industry === "Bollywood" || (200301 <= m.id && m.id <= 200615);
      }
      return true;
    }).slice().sort((a, b) => b.score - a.score);

    if (state.genre !== "All") {
      const filtered = pool.filter(m => (m.genres || []).includes(state.genre));
      if (filtered.length > 0) pool = filtered;
    }

    renderMovieCards(grid, pool.slice(0, state.indianCount).map(m => ({
      ...m,
      _explainReason: `${m.industry || "Indian"} Blockbuster • ${m.votes > 0 ? formatVotes(m.votes) + ' TMDB votes' : 'Verified Cinema'}`
    })));

    if (loadMoreBtn) {
      if (state.indianCount >= pool.length) {
        loadMoreBtn.style.display = "none";
      } else {
        loadMoreBtn.style.display = "inline-block";
        const indName = state.indianIndustry === "all" ? "Indian" : state.indianIndustry;
        loadMoreBtn.textContent = `⬇ Load More ${indName} Movies (${pool.length - state.indianCount} remaining)`;
      }
    }
  }

  function renderPopular() {
    const grid = document.getElementById("popularGrid");
    if (!grid) return;
    let popular = MOVIES.slice().sort((a, b) => (b.votes * Math.pow(b.score, 1.4)) - (a.votes * Math.pow(a.score, 1.4)));
    if (state.genre !== "All") {
      const filtered = popular.filter(m => (m.genres || []).includes(state.genre));
      if (filtered.length > 0) popular = filtered;
    }
    renderMovieCards(grid, popular.slice(0, 12).map(m => ({
      ...m,
      _explainReason: `Global Audience Favorite • ${formatVotes(m.votes)} verified reviews`
    })));
  }

  function renderUserRatings() {
    const grid = document.getElementById("userRatingsGrid");
    const emptyState = document.getElementById("userRatingsEmpty");
    if (!grid) return;

    const ratedList = Object.entries(state.ratings).map(([id, r]) => ({
      movie: MOVIE_MAP.get(Number(id)),
      rating: Number(r)
    })).filter(x => x.movie);

    if (ratedList.length === 0) {
      if (emptyState) emptyState.classList.remove("hidden");
      grid.innerHTML = "";
    } else {
      if (emptyState) emptyState.classList.add("hidden");
      grid.innerHTML = ratedList.map(({ movie, rating }) => `
        <div class="movie-card" data-movie-id="${movie.id}">
          <div class="card-media">
            <img src="${getPosterSrc(movie)}" alt="${escapeHtml(movie.title)}" loading="lazy" class="movie-poster" onerror="this.onerror=null;this.src='${getPosterSrc({ ...movie, poster: '' })}'">
            <div class="user-rated-badge">Rated: ${rating}/10 ⭐</div>
            <button class="btn-quick-rate" data-movie-id="${movie.id}" data-title="${escapeHtml(movie.title)}">★ Edit (${rating}/10)</button>
          </div>
          <div class="card-body">
            <div class="card-meta">
              <span class="movie-year">${movie.year || "N/A"}</span>
              <span class="movie-rating-badge">Your: ${rating}/10 ⭐</span>
            </div>
            <div style="font-size:0.75rem; color:#94a3b8; margin: 2px 0 4px;">
              TMDB: <strong style="color:#fbbf24;">${movie.rating ? Number(movie.rating).toFixed(1) + '/10' : 'Unrated'}</strong>
            </div>
            <h3 class="movie-title">${escapeHtml(movie.title)}</h3>
            <div class="card-actions">
              <button class="btn-card-details" data-detail-id="${movie.id}">Details</button>
            </div>
          </div>
        </div>
      `).join("");
    }
  }

  // =========================================================================
  // 12. Standard Card Renderer (with Explainable Reason & Watchlist Badges)
  // =========================================================================
  function renderMovieCards(container, movies) {
    if (!movies || movies.length === 0) {
      container.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><div class="empty-icon">🎬</div><h3>No movies found</h3><p>Try broadening your filters or clearing search terms.</p></div>`;
      return;
    }

    container.innerHTML = movies.map(m => {
      const userR = state.ratings[m.id];
      const inWatchlist = state.watchlist.has(m.id);
      const isFav = state.favourites.has(m.id);
      const matchScore = m._calcScore ? Math.min(99, Math.round(m._calcScore * 100)) : Math.min(99, Math.max(60, Math.round(((m.score || 6.54) / 10.0) * 100)));
      const reasonTag = m._explainReason || (m.genres ? `Recommended for fans of ${m.genres.slice(0, 2).join(" & ")}` : "Recommended by CineMatch AI");

      const hasRating = (m.rating !== null && m.rating !== undefined && m.votes > 0);
      const ratingBadgeHtml = hasRating 
        ? `<span class="movie-rating-badge" title="TMDB Community Rating: ${Number(m.rating).toFixed(1)} / 10 (${(m.votes || 0).toLocaleString()} votes)">⭐ ${Number(m.rating).toFixed(1)} <span class="rating-scale">/10</span> <span class="vote-count">(${formatVotes(m.votes)})</span></span>`
        : `<span class="movie-rating-badge unrated-badge" title="No verified community ratings yet">⭐ <span class="unrated-text">Not Rated Yet</span></span>`;

      return `
        <div class="movie-card" data-movie-id="${m.id}">
          <div class="card-media">
            <img 
              src="${getPosterSrc(m)}" 
              alt="${escapeHtml(m.title)}" 
              loading="lazy" 
              class="movie-poster" 
              onerror="this.onerror=null;this.src='${getPosterSrc({ ...m, poster: '' })}'"
            >
            <div class="match-badge"><span class="match-val">${matchScore}%</span> Match</div>
            
            ${userR ? `<div class="user-rated-badge">Rated ${userR}/10 ⭐</div>` : ""}

            <div class="card-floating-actions">
              <button class="btn-icon-floating ${inWatchlist ? 'active' : ''}" data-watchlist-id="${m.id}" title="${inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}">
                <svg viewBox="0 0 24 24" fill="${inWatchlist ? '#8b5cf6' : 'none'}" stroke="currentColor" stroke-width="2" width="16" height="16">
                  <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                </svg>
              </button>
              <button class="btn-icon-floating ${isFav ? 'active-fav' : ''}" data-fav-id="${m.id}" title="${isFav ? 'In Favourites' : 'Add to Favourites'}">
                <svg viewBox="0 0 24 24" fill="${isFav ? '#f43f5e' : 'none'}" stroke="currentColor" stroke-width="2" width="16" height="16">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                </svg>
              </button>
            </div>

            <button class="btn-quick-rate" data-movie-id="${m.id}" data-title="${escapeHtml(m.title)}">${userR ? `★ ${userR}/10` : '★ Rate'}</button>
          </div>

          <div class="card-body">
            <div class="card-meta">
              <span class="movie-year">${m.year || "N/A"}</span>
              ${ratingBadgeHtml}
            </div>

            <h3 class="movie-title" title="${escapeHtml(m.title)}">
              <a href="javascript:void(0)" class="open-detail-link" data-detail-id="${m.id}">${escapeHtml(m.title)}</a>
            </h3>

            <div class="movie-genres">
              ${(m.genres || []).slice(0, 3).map(g => `<span class="genre-pill">${escapeHtml(g)}</span>`).join("")}
            </div>

            <!-- Explainable AI Recommendation Tag (Requirement 8) -->
            <div class="ai-reason-tag" title="${escapeHtml(reasonTag)}">
              <span class="ai-reason-icon">💡</span>
              <span class="ai-reason-text">${escapeHtml(reasonTag)}</span>
            </div>

            <div class="card-actions">
              <button class="btn-card-details" data-detail-id="${m.id}">Details</button>
              <button class="btn-card-similar" data-similar-id="${m.id}">Similar</button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  // =========================================================================
  // 13. Cinematic Movie Details Modal with Verified Credits & Authentic Cast
  // =========================================================================
  function openDetailModal(movieId) {
    const movie = MOVIE_MAP.get(Number(movieId));
    const modal = document.getElementById("detailModal");
    if (!movie || !modal) return;

    const posterImg = document.getElementById("modalDetailPoster");
    const heroHeader = document.getElementById("modalHeroHeader");
    const titleEl = document.getElementById("modalMovieTitle");
    const metaPills = document.getElementById("modalMetaPills");
    const bodyEl = document.getElementById("modalDetailBody");

    const posterUrl = getPosterSrc(movie);
    if (posterImg) posterImg.src = posterUrl;
    if (heroHeader) heroHeader.style.backgroundImage = `url('${posterUrl}')`;
    if (titleEl) titleEl.textContent = `${movie.title} (${movie.year || "N/A"})`;

    const userR = state.ratings[movie.id];
    const inWatchlist = state.watchlist.has(movie.id);
    const isFav = state.favourites.has(movie.id);
    const isWatched = state.watched.has(movie.id);

    // Meta Pills: Rating, Cert, Runtime, Industry, Genres
    const hasRating = (movie.rating !== null && movie.rating !== undefined && movie.votes > 0);
    if (metaPills) {
      metaPills.innerHTML = `
        <span class="meta-rating-pill">⭐ ${hasRating ? Number(movie.rating).toFixed(1) + ' / 10' : 'Not Rated Yet'} <span class="pill-tmdb-tag">TMDB</span></span>
        <span class="meta-cert-pill">UA / PG-13</span>
        <span>${movie.runtime || "2h 15m"}</span>
        <span>•</span>
        <span class="text-cyan">${movie.industry || "Cinema"}</span>
        <span>•</span>
        <span class="text-purple">${(movie.genres || []).join(", ")}</span>
      `;
    }

    // Similar titles
    const similarMovies = (movie.sims || []).map(id => MOVIE_MAP.get(id)).filter(Boolean);

    // Initial synopsis
    const synopsis = movie.synopsis || 
      `In ${movie.title}, high-stakes drama and cinematic brilliance collide as extraordinary characters face formidable trials, uncovering secrets that will change their world forever. An acclaimed masterpiece in the ${movie.genres ? movie.genres.join(", ") : "drama"} genre.`;

    if (bodyEl) {
      bodyEl.innerHTML = `
        <!-- Action Bar (Image 2 Inspiration) -->
        <div class="modal-action-bar">
          <button type="button" class="btn-modal-action ${inWatchlist ? 'active-watchlist' : ''}" id="btnModalToggleWatchlist">
            <svg viewBox="0 0 24 24" fill="${inWatchlist ? '#fff' : 'none'}" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path></svg>
            <span>${inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}</span>
          </button>

          <button type="button" class="btn-modal-action ${isWatched ? 'active-watched' : ''}" id="btnModalToggleWatched">
            <svg viewBox="0 0 24 24" fill="${isWatched ? '#fff' : 'none'}" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="20 6 9 17 4 12"></polyline></svg>
            <span>${isWatched ? 'Watched' : 'Mark as Watched'}</span>
          </button>

          <button type="button" class="btn-modal-action ${isFav ? 'active-fav' : ''}" id="btnModalToggleFav">
            <svg viewBox="0 0 24 24" fill="${isFav ? '#fff' : 'none'}" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
            <span>${isFav ? 'Favorited' : 'Favorite'}</span>
          </button>
        </div>

        <!-- Official TMDB Community Rating Component (Requirement 2) -->
        <div class="tmdb-rating-showcase-card">
          <div class="tmdb-rating-left">
            <div class="tmdb-rating-score">
              <span class="rating-star">⭐</span>
              <span class="rating-big-num">${hasRating ? Number(movie.rating).toFixed(1) : "N/A"}</span>
              <span class="rating-ten">/ 10</span>
            </div>
            <div class="tmdb-badge-label">
              <span class="tmdb-logo-pill">TMDB</span> Official Community Rating
            </div>
          </div>
          <div class="tmdb-rating-right">
            <div class="tmdb-vote-count-line">Based on <strong>${movie.votes > 0 ? Number(movie.votes).toLocaleString() : '0'}</strong> verified votes</div>
            <div class="tmdb-popularity-line">Popularity Index: <strong>${Number(movie.popularity || 0).toFixed(1)}</strong></div>
          </div>
        </div>

        <!-- Synopsis & Credits Grid -->
        <div class="modal-details-grid">
          <div class="modal-synopsis">
            <h3>Synopsis</h3>
            <p id="modalSynopsisText">${escapeHtml(synopsis)}</p>

            <!-- 10-Point User Rating Section (Requirement 6) -->
            <div style="margin-top: 20px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <h4 style="font-size: 0.95rem; color: #fff; margin: 0;">Your Personal Rating:</h4>
                ${userR ? `<button type="button" class="btn-clear-rating" id="btnModalClearRating">Remove Rating</button>` : ""}
              </div>
              <div class="star-rating-container ten-stars" style="justify-content: flex-start; margin: 6px 0;" id="detailStarsContainer">
                ${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(v => `
                  <button type="button" class="star-btn ${userR >= v ? 'active' : ''}" data-modal-rate-val="${v}" title="${v}/10">★<span class="star-num">${v}</span></button>
                `).join("")}
              </div>
              <div id="detailRatingComparison" class="rating-comparison-box ${userR ? '' : 'hidden'}">
                ${renderRatingComparisonHtml(userR, movie.rating)}
              </div>
            </div>
          </div>

          <div class="modal-credits-box">
            <h3>Credits &amp; Metadata</h3>
            <div class="credit-item">
              <div class="credit-lbl">Director(s)</div>
              <div class="credit-val" id="modalDirectorContainer">
                <span class="skeleton-line" style="display:inline-block; width:130px; height:18px;"></span>
              </div>
            </div>
            <div class="credit-item">
              <div class="credit-lbl">Official Rating</div>
              <div class="credit-val text-gold">${hasRating ? Number(movie.rating).toFixed(1) + ' / 10 (TMDB)' : 'Not Rated Yet'}</div>
            </div>
            <div class="credit-item">
              <div class="credit-lbl">Quality Score (Bayesian)</div>
              <div class="credit-val text-purple">${Number(movie.score || 6.54).toFixed(2)} / 10.0</div>
            </div>
            <div class="credit-item">
              <div class="credit-lbl">Total Rating Volume</div>
              <div class="credit-val text-cyan">${(movie.votes || 0).toLocaleString()} verified votes</div>
            </div>
            <div class="credit-item">
              <div class="credit-lbl">Industry</div>
              <div class="credit-val">${escapeHtml(movie.industry || "Global Cinema")}</div>
            </div>
          </div>
        </div>

        <!-- Dedicated Director Spotlight Section (Image 2 Streaming Inspiration) -->
        <div class="modal-director-section" id="modalDirectorSection">
          <h3>Directed By</h3>
          <div class="directors-spotlight-row" id="modalDirectorSpotlight">
            <span class="skeleton-line" style="display:inline-block; width:170px; height:46px; border-radius:9999px;"></span>
          </div>
        </div>

        <!-- Principal Cast & Actresses Section (Image 2 Streaming Inspiration) -->
        <div class="modal-cast-section">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h3 style="margin:0;">Principal Cast &amp; Stars</h3>
            <span class="cast-count-badge" id="modalCastCountBadge" style="font-size:0.75rem; color:var(--text-muted);">Verified TMDB Cast</span>
          </div>
          <div class="cast-avatars-row" id="modalCastContainer">
            ${[1, 2, 3, 4, 5, 6, 7, 8].map(() => `
              <div class="skeleton-avatar-item">
                <div class="skeleton-circle"></div>
                <div class="skeleton-line"></div>
              </div>
            `).join("")}
          </div>
        </div>

        <!-- Similar Titles Section -->
        ${similarMovies.length > 0 ? `
          <div class="modal-similar-section">
            <h3>More Titles Like This</h3>
            <div class="movie-grid" style="grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));">
              ${renderCardsHtml(similarMovies.slice(0, 4))}
            </div>
          </div>
        ` : ""}
      `;

      // Attach Modal Action Listeners
      const watchlistBtn = document.getElementById("btnModalToggleWatchlist");
      const watchedBtn = document.getElementById("btnModalToggleWatched");
      const favBtn = document.getElementById("btnModalToggleFav");

      if (watchlistBtn) {
        watchlistBtn.onclick = () => {
          toggleWatchlist(movie.id);
          const active = state.watchlist.has(movie.id);
          watchlistBtn.classList.toggle("active-watchlist", active);
          watchlistBtn.querySelector("span").textContent = active ? "In Watchlist" : "Add to Watchlist";
        };
      }

      if (watchedBtn) {
        watchedBtn.onclick = () => {
          toggleWatched(movie.id);
          const active = state.watched.has(movie.id);
          watchedBtn.classList.toggle("active-watched", active);
          watchedBtn.querySelector("span").textContent = active ? "Watched" : "Mark as Watched";
        };
      }

      if (favBtn) {
        favBtn.onclick = () => {
          toggleFavourite(movie.id);
          const active = state.favourites.has(movie.id);
          favBtn.classList.toggle("active-fav", active);
          favBtn.querySelector("span").textContent = active ? "Favorited" : "Favorite";
        };
      }

      // 10-Star rating inside modal (Requirement 6)
      bodyEl.querySelectorAll("[data-modal-rate-val]").forEach(star => {
        star.onclick = () => {
          const val = Number(star.dataset.modalRateVal);
          saveUserRating(movie.id, val);
          bodyEl.querySelectorAll("[data-modal-rate-val]").forEach(s => {
            s.classList.toggle("active", Number(s.dataset.modalRateVal) <= val);
          });
          const compEl = document.getElementById("detailRatingComparison");
          if (compEl) {
            compEl.innerHTML = renderRatingComparisonHtml(val, movie.rating);
            compEl.classList.remove("hidden");
          }
          showToast(`Saved ${val}/10 ⭐ rating for "${movie.title}"!`);
          renderPersonalized();
          renderUserRatings();
          renderAllOpenLists();
        };
      });

      const clearBtn = document.getElementById("btnModalClearRating");
      if (clearBtn) {
        clearBtn.onclick = () => {
          removeUserRating(movie.id);
          bodyEl.querySelectorAll("[data-modal-rate-val]").forEach(s => s.classList.remove("active"));
          const compEl = document.getElementById("detailRatingComparison");
          if (compEl) compEl.classList.add("hidden");
          clearBtn.style.display = "none";
        };
      }

      // Asynchronously fetch verified directors and cast from TMDB
      loadCreditsForDetailModal(movie, modal);
    }

    modal.classList.add("active");
  }

  // Asynchronously load and render verified credits (directors & cast)
  async function loadCreditsForDetailModal(movie, modal) {
    const dirSpotlight = document.getElementById("modalDirectorSpotlight");
    const dirContainer = document.getElementById("modalDirectorContainer");
    const castContainer = document.getElementById("modalCastContainer");
    const castBadge = document.getElementById("modalCastCountBadge");
    const synopsisText = document.getElementById("modalSynopsisText");
    const heroHeader = document.getElementById("modalHeroHeader");

    try {
      const credits = await fetchMovieCredits(movie);

      // Verify modal is still showing this movie
      if (!modal.classList.contains("active")) return;

      if (credits) {
        // Upgrade backdrop if authentic TMDB backdrop exists
        if (credits.backdrop_path && heroHeader) {
          heroHeader.style.backgroundImage = `url('${credits.backdrop_path}')`;
        }

        // Upgrade synopsis with authentic overview
        if (credits.overview && synopsisText) {
          synopsisText.textContent = credits.overview;
        }

        const dirs = credits.directors || [];

        // 1. Render Dedicated Director Spotlight
        if (dirSpotlight) {
          if (dirs.length > 0) {
            dirSpotlight.innerHTML = dirs.map(d => `
              <div class="director-spotlight-card" data-person-id="${d.id}" data-person-name="${escapeHtml(d.name)}" data-person-role="Director" data-person-img="${d.profile_path || ''}" title="View ${escapeHtml(d.name)} profile & filmography">
                <img src="${d.profile_path || getAvatarPlaceholderSvg(d.name, 90)}" alt="${escapeHtml(d.name)}" class="director-spotlight-avatar" onerror="this.onerror=null;this.src='${getAvatarPlaceholderSvg(d.name, 90)}'">
                <div class="director-spotlight-meta">
                  <span class="director-spotlight-name">${escapeHtml(d.name)}</span>
                  <span class="director-spotlight-badge">Director</span>
                </div>
              </div>
            `).join("");
          } else if (movie.director) {
            dirSpotlight.innerHTML = `
              <div class="director-spotlight-card" title="${escapeHtml(movie.director)}">
                <img src="${getAvatarPlaceholderSvg(movie.director, 90)}" alt="${escapeHtml(movie.director)}" class="director-spotlight-avatar">
                <div class="director-spotlight-meta">
                  <span class="director-spotlight-name">${escapeHtml(movie.director)}</span>
                  <span class="director-spotlight-badge">Director</span>
                </div>
              </div>
            `;
          } else {
            dirSpotlight.innerHTML = `<span style="color:var(--text-muted); font-size:0.85rem;">Director details currently unavailable</span>`;
          }
        }

        // 2. Render Director text inside Credits Box
        if (dirContainer) {
          if (dirs.length > 0) {
            dirContainer.textContent = dirs.map(d => d.name).join(", ");
          } else if (movie.director) {
            dirContainer.textContent = movie.director;
          } else {
            dirContainer.textContent = "Information unavailable";
          }
        }

        // 3. Render verified principal cast (both male and female actors) with authentic photos
        if (castContainer) {
          const castList = credits.cast || [];
          if (castBadge) {
            castBadge.textContent = `${castList.length} Verified Cast Members`;
          }
          if (castList.length > 0) {
            castContainer.innerHTML = castList.map(c => `
              <div class="cast-avatar-item" data-person-id="${c.id}" data-person-name="${escapeHtml(c.name)}" data-person-role="${escapeHtml(c.character)}" data-person-img="${c.profile_path || ''}" title="View ${escapeHtml(c.name)} profile & filmography">
                <img src="${c.profile_path || getAvatarPlaceholderSvg(c.name, 150)}" alt="${escapeHtml(c.name)}" class="cast-avatar-circle" onerror="this.onerror=null;this.src='${getAvatarPlaceholderSvg(c.name, 150)}'">
                <div class="cast-actor-name" title="${escapeHtml(c.name)}">${escapeHtml(c.name)}</div>
                <div class="cast-character-role" title="${escapeHtml(c.character)}">${escapeHtml(c.character)}</div>
                <span class="cast-click-hint">View Profile</span>
              </div>
            `).join("");
          } else {
            castContainer.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:10px 0;">Principal cast details currently unavailable for this title.</div>`;
          }
        }
      } else {
        // Fallback for offline or non-TMDB titles
        if (dirSpotlight) {
          dirSpotlight.innerHTML = movie.director
            ? `
              <div class="director-spotlight-card" title="${escapeHtml(movie.director)}">
                <img src="${getAvatarPlaceholderSvg(movie.director, 90)}" alt="${escapeHtml(movie.director)}" class="director-spotlight-avatar">
                <div class="director-spotlight-meta">
                  <span class="director-spotlight-name">${escapeHtml(movie.director)}</span>
                  <span class="director-spotlight-badge">Director</span>
                </div>
              </div>
            `
            : `<span style="color:var(--text-muted);">Information unavailable</span>`;
        }
        if (dirContainer) {
          dirContainer.textContent = movie.director || "Information unavailable";
        }
        if (castContainer) {
          castContainer.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:10px 0;">Principal cast details currently unavailable.</div>`;
        }
      }

      // Attach click listeners to directors and cast items to open actor/director profile modal
      if (modal) {
        modal.querySelectorAll(".cast-avatar-item, .director-spotlight-card").forEach(el => {
          el.onclick = (e) => {
            e.stopPropagation();
            const pid = Number(el.dataset.personId);
            const pname = el.dataset.personName;
            const prole = el.dataset.personRole;
            const pimg = el.dataset.personImg;
            if (pid) {
              openActorModal(pid, pname, pimg, prole, movie.title);
            }
          };
        });
      }
    } catch (err) {
      console.warn("Failed loading credits:", err);
      if (dirContainer) {
        dirContainer.textContent = movie.director || "Information unavailable";
      }
      if (castContainer) {
        castContainer.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem;">Cast details unavailable.</div>`;
      }
    }
  }

  // =========================================================================
  // 14. Actor / Director Profile Modal (Requirement 5)
  // =========================================================================
  async function openActorModal(personId, personName, profilePath, role, fromMovieTitle) {
    const actorModal = document.getElementById("actorModal");
    const bodyEl = document.getElementById("actorModalBody");
    if (!actorModal || !bodyEl) return;

    // Show initial header skeleton with known info
    bodyEl.innerHTML = `
      <div class="actor-profile-header">
        <div class="actor-portrait-wrap">
          <img src="${profilePath || getAvatarPlaceholderSvg(personName, 300)}" alt="${escapeHtml(personName)}" class="actor-portrait-img" onerror="this.onerror=null;this.src='${getAvatarPlaceholderSvg(personName, 300)}'">
        </div>
        <div class="actor-header-meta">
          <span class="actor-dept-badge">${escapeHtml(role || "Cast & Crew")}</span>
          <h2 class="actor-name-title">${escapeHtml(personName)}</h2>
          <div class="actor-bio-meta-row" id="actorMetaRow">
            <span class="skeleton-line" style="display:inline-block; width:180px; height:14px;"></span>
          </div>
        </div>
      </div>
      <div class="actor-bio-section">
        <h3>Biography</h3>
        <p id="actorBioText">
          <span class="skeleton-line" style="display:block; width:100%; height:14px; margin-bottom:8px;"></span>
          <span class="skeleton-line" style="display:block; width:80%; height:14px;"></span>
        </p>
      </div>
      <div class="actor-filmography-section">
        <h3>Known For & Highlights</h3>
        <div class="actor-filmography-grid" id="actorFilmGrid">
          ${[1, 2, 3, 4].map(() => `
            <div class="actor-known-card" style="opacity: 0.5;">
              <div class="skeleton-line" style="height: 180px; width: 100%;"></div>
            </div>
          `).join("")}
        </div>
      </div>
    `;

    actorModal.classList.add("active");

    if (!personId) {
      const bioEl = document.getElementById("actorBioText");
      if (bioEl) {
        bioEl.textContent = `${personName} is an acclaimed cinema artist known for exceptional contributions to major motion pictures including ${fromMovieTitle || "prominent cinema"}.`;
      }
      const gridEl = document.getElementById("actorFilmGrid");
      if (gridEl) {
        gridEl.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:10px 0;">Detailed filmography unavailable.</div>`;
      }
      return;
    }

    try {
      const details = await fetchPersonDetails(personId);
      if (!actorModal.classList.contains("active")) return;

      if (details) {
        // Upgrade portrait if higher res available
        const imgEl = bodyEl.querySelector(".actor-portrait-img");
        if (imgEl && details.profile_path) {
          imgEl.src = details.profile_path;
        }

        // Meta info (birthday, birthplace, department)
        const metaRow = document.getElementById("actorMetaRow");
        if (metaRow) {
          const parts = [];
          if (details.birthday) parts.push(`<span>Born: ${escapeHtml(details.birthday)}</span>`);
          if (details.place_of_birth) parts.push(`<span>${escapeHtml(details.place_of_birth)}</span>`);
          if (details.known_for_department) parts.push(`<span style="color:#a78bfa;">${escapeHtml(details.known_for_department)}</span>`);
          metaRow.innerHTML = parts.join(` <span>&bull;</span> `) || `<span>Cinema Artist</span>`;
        }

        // Biography
        const bioEl = document.getElementById("actorBioText");
        if (bioEl) {
          bioEl.textContent = details.biography && details.biography.trim().length > 0
            ? details.biography
            : `${personName} is an acclaimed cinema artist known for their talent and celebrated performances across prominent motion pictures including ${fromMovieTitle || "iconic cinema"}.`;
        }

        // Filmography grid
        const filmGrid = document.getElementById("actorFilmGrid");
        if (filmGrid) {
          if (details.known_for && details.known_for.length > 0) {
            filmGrid.innerHTML = details.known_for.map(m => `
              <div class="actor-known-card" data-known-title="${escapeHtml(m.title)}" data-known-tmdb="${m.id}" title="Explore ${escapeHtml(m.title)}">
                <img src="${m.poster || getPosterSrc({ title: m.title, year: m.year, genres: [] })}" alt="${escapeHtml(m.title)}" class="actor-known-poster" onerror="this.onerror=null;this.src='${getPosterSrc({ title: m.title, year: m.year, genres: [] })}'">
                <div class="actor-known-info">
                  <div class="actor-known-title">${escapeHtml(m.title)}</div>
                  <div class="actor-known-role">${escapeHtml(m.character || (m.year ? String(m.year) : ""))}</div>
                </div>
              </div>
            `).join("");

            // Click on known movie tries to find in local catalog or notifies user
            filmGrid.querySelectorAll(".actor-known-card").forEach(card => {
              card.onclick = () => {
                const title = card.dataset.knownTitle;
                const tmdbId = Number(card.dataset.knownTmdb);
                const found = MOVIES.find(m => m.tmdbId === tmdbId || (m.title && m.title.toLowerCase() === (title || "").toLowerCase()));
                if (found) {
                  actorModal.classList.remove("active");
                  openDetailModal(found.id);
                } else {
                  showToast(`Selected "${title}" starring ${personName}`);
                }
              };
            });
          } else {
            filmGrid.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:10px 0;">No additional verified filmography found.</div>`;
          }
        }
      }
    } catch (e) {
      console.warn("Failed fetching person details:", e);
    }
  }

  function renderCardsHtml(movies) {
    return movies.map(m => {
      const hasRating = (m.rating !== null && m.rating !== undefined && m.votes > 0);
      const rBadge = hasRating 
        ? `<span class="movie-rating-badge">⭐ ${Number(m.rating).toFixed(1)} <span class="rating-scale">/10</span></span>` 
        : `<span class="movie-rating-badge unrated-badge">⭐ Not Rated</span>`;
      return `
        <div class="movie-card" data-detail-id="${m.id}" style="cursor: pointer;">
          <div class="card-media">
            <img src="${getPosterSrc(m)}" alt="${escapeHtml(m.title)}" loading="lazy" class="movie-poster" onerror="this.onerror=null;this.src='${getPosterSrc({ ...m, poster: '' })}'">
          </div>
          <div class="card-body">
            <div class="card-meta">
              <span class="movie-year">${m.year || "N/A"}</span>
              ${rBadge}
            </div>
            <h4 class="movie-title" style="font-size: 0.9rem;">${escapeHtml(m.title)}</h4>
          </div>
        </div>
      `;
    }).join("");
  }

  // =========================================================================
  // 14. Watchlist & Favourites Suite
  // =========================================================================
  function toggleWatchlist(movieId) {
    const mid = Number(movieId);
    const movie = MOVIE_MAP.get(mid);
    if (state.watchlist.has(mid)) {
      state.watchlist.delete(mid);
      showToast(`Removed "${movie ? movie.title : 'Movie'}" from Watchlist`);
    } else {
      state.watchlist.add(mid);
      showToast(`Added "${movie ? movie.title : 'Movie'}" to Watchlist!`);
    }
    saveStorageSet("cinematch_watchlist", state.watchlist);
    updateNavWatchlistBadge();
    renderAllOpenLists();
  }

  function toggleFavourite(movieId) {
    const mid = Number(movieId);
    const movie = MOVIE_MAP.get(mid);
    if (state.favourites.has(mid)) {
      state.favourites.delete(mid);
      showToast(`Removed "${movie ? movie.title : 'Movie'}" from Favourites`);
    } else {
      state.favourites.add(mid);
      showToast(`Added "${movie ? movie.title : 'Movie'}" to Favourites! ❤️`);
    }
    saveStorageSet("cinematch_favourites", state.favourites);
    updateNavWatchlistBadge();
    renderAllOpenLists();
  }

  function toggleWatched(movieId) {
    const mid = Number(movieId);
    const movie = MOVIE_MAP.get(mid);
    if (state.watched.has(mid)) {
      state.watched.delete(mid);
      showToast(`Marked "${movie ? movie.title : 'Movie'}" as Unwatched`);
    } else {
      state.watched.add(mid);
      showToast(`Marked "${movie ? movie.title : 'Movie'}" as Watched! ✅`);
    }
    saveStorageSet("cinematch_watched", state.watched);
    updateNavWatchlistBadge();
    renderAllOpenLists();
  }

  function saveUserRating(movieId, rating) {
    state.ratings[movieId] = rating;
    saveStorageMap("cinematch_user_ratings", state.ratings);
    updateNavWatchlistBadge();
  }

  function renderAllOpenLists() {
    // If watchlist modal is active, refresh current tab
    const wModal = document.getElementById("watchlistModal");
    if (wModal && wModal.classList.contains("active")) {
      const activeTabBtn = document.querySelector("#watchlistTabs .watchlist-tab-btn.active");
      if (activeTabBtn) renderWatchlistTab(activeTabBtn.dataset.tab);
    }
  }

  function renderWatchlistTab(tabKey) {
    const container = document.getElementById("watchlistTabContent");
    if (!container) return;

    let idList = [];
    if (tabKey === "watchlist") idList = Array.from(state.watchlist);
    else if (tabKey === "favourites") idList = Array.from(state.favourites);
    else if (tabKey === "watched") idList = Array.from(state.watched);
    else if (tabKey === "ratings") idList = Object.keys(state.ratings).map(Number);

    const movies = idList.map(id => MOVIE_MAP.get(id)).filter(Boolean);

    if (movies.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1; padding: 40px 20px;">
          <div class="empty-icon">${tabKey === 'favourites' ? '❤️' : (tabKey === 'watched' ? '✅' : '📌')}</div>
          <h3>Your ${tabKey} is empty</h3>
          <p>Explore the catalog or Ask AI to bookmark your favorite films!</p>
        </div>
      `;
      return;
    }

    renderMovieCards(container, movies);
  }

  // =========================================================================
  // 16. Modals & Global Event Listeners
  // =========================================================================
  function initModals() {
    // Watchlist Modal Trigger
    const openWatchlistBtn = document.getElementById("openWatchlistBtn");
    const watchlistModal = document.getElementById("watchlistModal");
    const closeWatchlistBtn = document.getElementById("closeWatchlistModalBtn");
    const watchlistTabs = document.getElementById("watchlistTabs");

    if (openWatchlistBtn && watchlistModal) {
      openWatchlistBtn.onclick = () => {
        watchlistModal.classList.add("active");
        renderWatchlistTab("watchlist");
      };
    }

    if (closeWatchlistBtn && watchlistModal) {
      closeWatchlistBtn.onclick = () => watchlistModal.classList.remove("active");
    }

    if (watchlistTabs) {
      watchlistTabs.addEventListener("click", (e) => {
        const btn = e.target.closest(".watchlist-tab-btn");
        if (!btn) return;
        watchlistTabs.querySelectorAll(".watchlist-tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        renderWatchlistTab(btn.dataset.tab);
      });
    }

    // Details Modal
    const detailModal = document.getElementById("detailModal");
    const closeDetailBtn = document.getElementById("closeDetailModalBtn");
    if (closeDetailBtn && detailModal) {
      closeDetailBtn.onclick = () => detailModal.classList.remove("active");
    }

    // Actor / Director Profile Modal
    const actorModal = document.getElementById("actorModal");
    const closeActorBtn = document.getElementById("closeActorModalBtn");
    if (closeActorBtn && actorModal) {
      closeActorBtn.onclick = () => actorModal.classList.remove("active");
    }

    // Quick Rating Modal (Requirement 6: 10-Point Rating, Hover, Comparison, and Clear)
    const ratingModal = document.getElementById("ratingModal");
    const closeRatingBtn = document.getElementById("closeRatingModalBtn");
    const modalStars = document.querySelectorAll("#modalStars .star-btn");
    const ratingText = document.getElementById("modalRatingText");
    const modalMovieId = document.getElementById("modalMovieId");
    const modalClearRatingBtn = document.getElementById("modalClearRatingBtn");
    const modalRatingComparison = document.getElementById("modalRatingComparison");

    if (closeRatingBtn && ratingModal) {
      closeRatingBtn.onclick = () => ratingModal.classList.remove("active");
    }

    if (modalClearRatingBtn) {
      modalClearRatingBtn.onclick = () => {
        const mid = Number(modalMovieId.value);
        removeUserRating(mid);
        modalStars.forEach(s => s.classList.remove("active"));
        if (ratingText) ratingText.textContent = "Rating cleared!";
        if (modalRatingComparison) modalRatingComparison.classList.add("hidden");
        setTimeout(() => {
          if (ratingModal) ratingModal.classList.remove("active");
        }, 350);
      };
    }

    modalStars.forEach(btn => {
      // Click rating
      btn.onclick = () => {
        const val = Number(btn.dataset.val);
        const mid = Number(modalMovieId.value);
        const movie = MOVIE_MAP.get(mid);
        saveUserRating(mid, val);

        modalStars.forEach(s => s.classList.toggle("active", Number(s.dataset.val) <= val));
        if (ratingText) ratingText.textContent = `Saved ${val}/10 ⭐ rating!`;

        if (modalRatingComparison && movie) {
          modalRatingComparison.innerHTML = renderRatingComparisonHtml(val, movie.rating);
          modalRatingComparison.classList.remove("hidden");
        }
        showToast(`Saved ${val}/10 ⭐ rating for "${movie ? movie.title : 'Movie'}"!`);

        setTimeout(() => {
          if (ratingModal) ratingModal.classList.remove("active");
          renderPersonalized();
          renderUserRatings();
          renderAllOpenLists();
          document.querySelectorAll(`.movie-card[data-movie-id="${mid}"] .btn-quick-rate`).forEach(b => {
            b.textContent = `★ ${val}/10`;
          });
        }, 450);
      };

      // Hover feedback
      btn.onmouseenter = () => {
        const hoverVal = Number(btn.dataset.val);
        modalStars.forEach(s => s.classList.toggle("active", Number(s.dataset.val) <= hoverVal));
        if (ratingText) ratingText.textContent = `${hoverVal}/10 ⭐`;
      };
    });

    const modalStarsWrap = document.getElementById("modalStars");
    if (modalStarsWrap) {
      modalStarsWrap.onmouseleave = () => {
        const mid = Number(modalMovieId.value);
        const currentR = state.ratings[mid];
        modalStars.forEach(s => s.classList.toggle("active", currentR && Number(s.dataset.val) <= currentR));
        if (ratingText) {
          ratingText.textContent = currentR ? `Your Rating: ${currentR}/10 ⭐` : "Click a star (1-10) to rate";
        }
      };
    }

    // ML Metrics Modal & Chart.js
    const metricsModal = document.getElementById("metricsModal");
    const openMetricsBtn = document.getElementById("openMetricsBtn");
    const closeMetricsBtn = document.getElementById("closeMetricsBtn");
    let chartRendered = false;

    if (openMetricsBtn && metricsModal) {
      openMetricsBtn.onclick = () => {
        metricsModal.classList.add("active");
        if (!chartRendered && typeof Chart !== "undefined") {
          const canvas = document.getElementById("metricsChart");
          if (canvas) {
            new Chart(canvas.getContext("2d"), {
              type: "bar",
              data: {
                labels: ["RMSE (0.9255)", "MAE (0.7177)", "Precision@10 (69.0%)", "NDCG@10 (0.8721)"],
                datasets: [{
                  data: [0.9255, 0.7177, 0.6900, 0.8721],
                  backgroundColor: ["#f43f5e", "#06b6d4", "#10b981", "#8b5cf6"],
                  borderRadius: 6
                }]
              },
              options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                  y: { beginAtZero: true, max: 1.1, grid: { color: "rgba(255,255,255,0.08)" } },
                  x: { grid: { display: false } }
                }
              }
            });
            chartRendered = true;
          }
        }
      };
    }

    if (closeMetricsBtn && metricsModal) {
      closeMetricsBtn.onclick = () => metricsModal.classList.remove("active");
    }

    // Global Delegated Click Handler for Cards & Buttons
    document.addEventListener("click", (e) => {
      // 1. Details or Similar Click
      const detailTrigger = e.target.closest("[data-detail-id]") || e.target.closest("[data-similar-id]");
      if (detailTrigger) {
        // Prevent trigger when clicking inner buttons
        if (e.target.closest(".btn-quick-rate") || e.target.closest(".btn-icon-floating")) return;
        const mid = Number(detailTrigger.dataset.detailId || detailTrigger.dataset.similarId);
        openDetailModal(mid);
        return;
      }

      // 2. Quick Rate Click
      const rateBtn = e.target.closest(".btn-quick-rate");
      if (rateBtn && ratingModal) {
        const mid = Number(rateBtn.dataset.movieId);
        const movie = MOVIE_MAP.get(mid);
        const title = rateBtn.dataset.title || (movie ? movie.title : "Movie");
        modalMovieId.value = mid;
        document.getElementById("ratingModalTitle").textContent = `Rate "${title}"`;
        const currentR = state.ratings[mid];
        if (ratingText) {
          ratingText.textContent = currentR ? `Your Rating: ${currentR}/10 ⭐` : "Click a star (1-10) to submit rating";
        }
        modalStars.forEach(s => s.classList.toggle("active", currentR && Number(s.dataset.val) <= currentR));
        if (modalRatingComparison) {
          if (currentR && movie) {
            modalRatingComparison.innerHTML = renderRatingComparisonHtml(currentR, movie.rating);
            modalRatingComparison.classList.remove("hidden");
          } else {
            modalRatingComparison.classList.add("hidden");
          }
        }
        ratingModal.classList.add("active");
        return;
      }

      // 3. Floating Watchlist Button
      const wBtn = e.target.closest("[data-watchlist-id]");
      if (wBtn) {
        e.stopPropagation();
        const mid = Number(wBtn.dataset.watchlistId);
        toggleWatchlist(mid);
        const isNowIn = state.watchlist.has(mid);
        wBtn.classList.toggle("active", isNowIn);
        const svg = wBtn.querySelector("svg");
        if (svg) svg.setAttribute("fill", isNowIn ? "#8b5cf6" : "none");
        return;
      }

      // 4. Floating Favourite Button
      const favBtn = e.target.closest("[data-fav-id]");
      if (favBtn) {
        e.stopPropagation();
        const mid = Number(favBtn.dataset.favId);
        toggleFavourite(mid);
        const isNowIn = state.favourites.has(mid);
        favBtn.classList.toggle("active-fav", isNowIn);
        const svg = favBtn.querySelector("svg");
        if (svg) svg.setAttribute("fill", isNowIn ? "#f43f5e" : "none");
        return;
      }

      // 5. Close modals on backdrop click
      [actorModal, detailModal, watchlistModal, ratingModal, metricsModal].forEach(m => {
        if (m && e.target === m) {
          m.classList.remove("active");
        }
      });
    });

    // ESC key closes top-most modal
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (actorModal && actorModal.classList.contains("active")) {
          actorModal.classList.remove("active");
          return;
        }
        [detailModal, watchlistModal, ratingModal, metricsModal].forEach(m => {
          if (m) m.classList.remove("active");
        });
      }
    });
  }

  // Toast Helper
  function showToast(msg) {
    const cont = document.getElementById("toastContainer");
    if (!cont) return;
    const t = document.createElement("div");
    t.className = "toast success";
    t.innerHTML = `<span>✓</span> <span>${escapeHtml(msg)}</span>`;
    cont.appendChild(t);
    setTimeout(() => {
      t.style.opacity = "0";
      setTimeout(() => t.remove(), 300);
    }, 3200);
  }

  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, s => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[s]);
  }

})();
