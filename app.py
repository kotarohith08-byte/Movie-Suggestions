"""
app.py - CineMatch AI Flask Application Server
==============================================
Production-ready Flask application providing web UI routes,
RESTful recommendation APIs, movie search, user rating persistence,
and real-time ML model diagnostics.
"""

import os
import re
import html
from flask import Flask, request, jsonify, render_template, session, make_response, redirect, url_for
from recommender import get_recommender
import database as db

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "cinematch-ai-secret-key-production-local")

# Initialize database schema
db.init_db()

# Load recommender singleton
recommender = get_recommender()

# Load TMDB ID map for instant authentic poster lookups
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "8265bd1679663a7ea12ac168da84d2e8")
tmdb_map = {}
links_path = os.path.join(BASE_DIR, "data", "links.csv")
if os.path.exists(links_path):
    try:
        import pandas as pd
        _ldf = pd.read_csv(links_path).dropna(subset=["movieId", "tmdbId"])
        tmdb_map = dict(zip(_ldf["movieId"].astype(int), _ldf["tmdbId"].astype(int)))
    except Exception as e:
        print(f"[!] Warning reading links.csv: {e}")

# Genre color palette dictionary for SVG poster generator
GENRE_PALETTES = {
    "action": ("#e11d48", "#881337", "#f43f5e"),
    "adventure": ("#d97706", "#78350f", "#f59e0b"),
    "animation": ("#06b6d4", "#164e63", "#22d3ee"),
    "children": ("#10b981", "#064e3b", "#34d399"),
    "comedy": ("#f59e0b", "#7c2d12", "#fbbf24"),
    "crime": ("#475569", "#0f172a", "#94a3b8"),
    "documentary": ("#0d9488", "#134e4a", "#2dd4bf"),
    "drama": ("#6366f1", "#312e81", "#818cf8"),
    "fantasy": ("#8b5cf6", "#4c1d95", "#a78bfa"),
    "film-noir": ("#334155", "#020617", "#64748b"),
    "horror": ("#991b1b", "#450a0a", "#ef4444"),
    "musical": ("#d946ef", "#701a75", "#e879f9"),
    "mystery": ("#0284c7", "#0c4a6e", "#38bdf8"),
    "romance": ("#ec4899", "#831843", "#f472b6"),
    "sci-fi": ("#2563eb", "#1e3a8a", "#60a5fa"),
    "thriller": ("#ea580c", "#7c2d12", "#fb923c"),
    "war": ("#713f12", "#3b1e06", "#a16207"),
    "western": ("#b45309", "#451a03", "#d97706"),
}


def get_current_user_id() -> str:
    """Retrieves or initializes local session user ID."""
    if "user_id" not in session:
        session["user_id"] = "user_guest"
    return str(session["user_id"])


# =========================================================================
# Web UI Routes
# =========================================================================

@app.route("/")
def index():
    """Renders CineMatch AI homepage with discovery sections."""
    user_id = get_current_user_id()
    genres = recommender.all_genres
    user_ratings = db.get_user_ratings(user_id)
    user_preferences = db.get_user_preferences(user_id)

    # Initial recommendations: hybrid recommendations for active user
    personalized = recommender.get_hybrid_recommendations(
        user_id=user_id,
        user_local_ratings=user_ratings,
        preferred_genres=user_preferences,
        top_n=8
    )

    popular_movies = recommender.get_popular_movies(limit=8)
    top_rated_movies = recommender.get_top_rated_movies(limit=8)

    return render_template(
        "index.html",
        user_id=user_id,
        genres=genres,
        user_ratings_count=len(user_ratings),
        user_preferences=user_preferences,
        personalized_movies=personalized,
        popular_movies=popular_movies,
        top_rated_movies=top_rated_movies,
        metrics=recommender.evaluation_metrics
    )


@app.route("/search")
def search_page():
    """Handles movie search requests with text query, genre, and year filters."""
    query = request.args.get("q", "").strip()
    genre = request.args.get("genre", "All").strip()
    year_str = request.args.get("year", "").strip()

    year = None
    if year_str.isdigit():
        year = int(year_str)

    results = recommender.search_movies(query=query, genre=genre, year=year, limit=36)
    user_id = get_current_user_id()
    user_ratings_map = {r["movie_id"]: r["rating"] for r in db.get_user_ratings(user_id)}

    return render_template(
        "search.html",
        query=query,
        selected_genre=genre,
        selected_year=year_str,
        genres=recommender.all_genres,
        results=results,
        results_count=len(results),
        user_ratings_map=user_ratings_map
    )


@app.route("/movie/<int:movie_id>")
def movie_details_page(movie_id: int):
    """Movie details page with metadata, user rating control, and similar movies."""
    movie = recommender.get_movie_details(movie_id)
    if not movie:
        return render_template("404.html", message=f"Movie ID {movie_id} was not found in the dataset."), 404

    user_id = get_current_user_id()
    user_rating = db.get_user_rating_for_movie(user_id, movie_id)
    similar_movies = recommender.get_content_based_recommendations(movie_id, top_n=8)

    return render_template(
        "movie.html",
        movie=movie,
        user_rating=user_rating,
        similar_movies=similar_movies,
        user_id=user_id
    )


@app.route("/recommend/<int:movie_id>")
def recommend_similar_movies(movie_id: int):
    """Returns content-based recommendations for a target movie as HTML or JSON."""
    similar = recommender.get_content_based_recommendations(movie_id, top_n=12)
    movie = recommender.get_movie_details(movie_id)

    if request.headers.get("Accept") == "application/json" or request.args.get("format") == "json":
        return jsonify({
            "target_movie": movie,
            "recommendations": similar,
            "count": len(similar)
        })

    if not movie:
        return render_template("404.html", message="Movie not found"), 404

    return render_template(
        "similar.html",
        target_movie=movie,
        similar_movies=similar
    )


# =========================================================================
# REST API Endpoints
# =========================================================================

@app.route("/api/recommendations", methods=["GET"])
def api_recommendations():
    """
    Returns recommendations tailored to user preferences and rating history.
    Query parameters:
    - user_id: string (optional, defaults to current session)
    - algorithm: 'hybrid' | 'content' | 'collaborative' | 'popular' (default: hybrid)
    - top_n: integer (default: 12)
    - w_content, w_collab, w_genre, w_quality: floats (optional weights)
    """
    user_id = request.args.get("user_id", get_current_user_id())
    algorithm = request.args.get("algorithm", "hybrid").lower()
    top_n = min(50, max(1, int(request.args.get("top_n", 12))))

    user_ratings = db.get_user_ratings(user_id)
    user_preferences = db.get_user_preferences(user_id)

    # Allow custom ensemble weights
    weights = None
    if "w_content" in request.args or "w_collab" in request.args:
        try:
            weights = {
                "content": float(request.args.get("w_content", 0.35)),
                "collaborative": float(request.args.get("w_collab", 0.35)),
                "genre": float(request.args.get("w_genre", 0.15)),
                "quality": float(request.args.get("w_quality", 0.15))
            }
        except ValueError:
            weights = None

    if algorithm == "collaborative":
        recs = recommender.get_collaborative_recommendations(
            user_id=user_id,
            user_local_ratings=user_ratings,
            top_n=top_n
        )
    elif algorithm == "content":
        # Aggregate content recs based on user's highest rated movies
        if user_ratings:
            top_rated = sorted(user_ratings, key=lambda x: x["rating"], reverse=True)[0]
            recs = recommender.get_content_based_recommendations(top_rated["movie_id"], top_n=top_n)
        else:
            recs = recommender.get_top_rated_movies(limit=top_n)
    elif algorithm == "popular":
        recs = recommender.get_popular_movies(limit=top_n)
    else:  # hybrid
        recs = recommender.get_hybrid_recommendations(
            user_id=user_id,
            user_local_ratings=user_ratings,
            preferred_genres=user_preferences,
            top_n=top_n,
            weights=weights
        )

    return jsonify({
        "status": "success",
        "user_id": user_id,
        "algorithm": algorithm,
        "recommendations": recs,
        "count": len(recs),
        "user_ratings_count": len(user_ratings),
        "preferred_genres": user_preferences
    })


@app.route("/rate", methods=["POST"])
def rate_movie():
    """
    Submits or updates a 0.5 - 5.0 star rating for a movie.
    Accepts JSON payload or form data:
    { "movie_id": 1, "rating": 4.5, "user_id": "optional" }
    """
    data = request.get_json(silent=True) or request.form.to_dict()

    if not data or "movie_id" not in data or "rating" not in data:
        return jsonify({"status": "error", "message": "Missing required fields: movie_id and rating"}), 400

    try:
        movie_id = int(data["movie_id"])
        rating = float(data["rating"])
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "movie_id must be integer, rating must be float"}), 400

    if not (0.5 <= rating <= 5.0):
        return jsonify({"status": "error", "message": "Rating must be between 0.5 and 5.0 stars"}), 400

    movie = recommender.get_movie_details(movie_id)
    if not movie:
        return jsonify({"status": "error", "message": f"Movie ID {movie_id} does not exist"}), 404

    user_id = str(data.get("user_id") or get_current_user_id())
    result = db.save_rating(user_id=user_id, movie_id=movie_id, rating=rating)

    return jsonify({
        "status": "success",
        "message": f"Rating of {rating}★ saved for '{movie['clean_title']}'",
        "data": result
    })


@app.route("/api/user/ratings", methods=["GET"])
def get_user_ratings_api():
    """Returns all ratings for the current user, joined with movie metadata."""
    user_id = request.args.get("user_id", get_current_user_id())
    ratings = db.get_user_ratings(user_id)

    enriched = []
    for r in ratings:
        movie = recommender.get_movie_details(r["movie_id"])
        if movie:
            enriched.append({
                "movie_id": r["movie_id"],
                "rating": r["rating"],
                "updated_at": r["updated_at"],
                "title": movie["clean_title"],
                "year": movie["year"],
                "genres": movie["genres"],
                "genres_str": movie["genres_str"],
                "poster_url": movie["poster_url"]
            })

    return jsonify({
        "status": "success",
        "user_id": user_id,
        "ratings": enriched,
        "count": len(enriched)
    })


@app.route("/api/user/preferences", methods=["GET", "POST"])
def user_preferences_api():
    """GET or POST favorite genres preferences for user."""
    user_id = request.args.get("user_id") or get_current_user_id()

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        genres = data.get("genres", [])
        if isinstance(genres, str):
            genres = [g.strip() for g in genres.split(",") if g.strip()]
        db.save_user_preferences(user_id, genres)
        return jsonify({
            "status": "success",
            "message": "Preferences saved successfully",
            "preferred_genres": genres
        })

    saved = db.get_user_preferences(user_id)
    return jsonify({
        "status": "success",
        "user_id": user_id,
        "preferred_genres": saved
    })


@app.route("/api/user/switch", methods=["POST"])
def switch_user():
    """Allows testing different user personas or profiles."""
    data = request.get_json(silent=True) or request.form.to_dict()
    new_user_id = data.get("user_id", "").strip() if data else ""
    if not new_user_id:
        return jsonify({"status": "error", "message": "user_id cannot be blank"}), 400

    session["user_id"] = new_user_id
    return jsonify({"status": "success", "user_id": new_user_id})


@app.route("/api/genres", methods=["GET"])
def api_genres():
    """Returns available genres with total movie counts."""
    return jsonify({
        "status": "success",
        "genres": recommender.all_genres,
        "count": len(recommender.all_genres)
    })


@app.route("/api/popular", methods=["GET"])
def api_popular():
    """Returns top popular movies."""
    limit = min(50, max(1, int(request.args.get("limit", 12))))
    genre = request.args.get("genre")
    movies = recommender.get_popular_movies(limit=limit, genre=genre)
    return jsonify({"status": "success", "movies": movies, "count": len(movies)})


@app.route("/api/top-rated", methods=["GET"])
def api_top_rated():
    """Returns top rated movies."""
    limit = min(50, max(1, int(request.args.get("limit", 12))))
    genre = request.args.get("genre")
    movies = recommender.get_top_rated_movies(limit=limit, genre=genre)
    return jsonify({"status": "success", "movies": movies, "count": len(movies)})


@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    """Returns genuine calculated Machine Learning evaluation metrics."""
    return jsonify({
        "status": "success",
        "metrics": recommender.evaluation_metrics
    })


@app.route("/health", methods=["GET"])
def health():
    """Service health check."""
    return jsonify({
        "status": "healthy",
        "service": "CineMatch AI Recommendation System",
        "version": "1.0.0",
        "movies_loaded": len(recommender.movie_dict),
        "genres_loaded": len(recommender.all_genres),
        "database": os.path.exists(db.DB_PATH)
    })


# =========================================================================
# Dynamic Cinematic SVG Poster Generator
# =========================================================================

@app.route("/poster/<int:movie_id>")
def movie_poster(movie_id: int):
    """
    Returns authentic movie poster if cached or resolvable.
    Falls back gracefully to dynamic, high-resolution SVG poster
    when fallback=svg is requested or if poster is unavailable.
    """
    fallback_requested = request.args.get("fallback") == "svg"

    # If authentic poster is cached and SVG fallback wasn't explicitly requested
    if not fallback_requested:
        mid_str = str(movie_id)
        cached_url = getattr(recommender, "posters_cache", {}).get(mid_str)
        if cached_url:
            return redirect(cached_url, code=302)

        # On-demand lookup: 1. TMDB -> 2. Wikipedia
        found_url = None
        t_id = tmdb_map.get(movie_id)
        if t_id:
            try:
                import requests
                r = requests.get(f"https://api.themoviedb.org/3/movie/{t_id}?api_key={TMDB_API_KEY}", timeout=2.5)
                if r.status_code == 200:
                    p = r.json().get("poster_path")
                    if p:
                        found_url = f"https://image.tmdb.org/t/p/w500{p}"
            except Exception:
                pass

        if not found_url:
            movie = recommender.get_movie_details(movie_id)
            if movie:
                try:
                    from fetch_posters import fetch_poster_from_wikipedia
                    found_url = fetch_poster_from_wikipedia(movie["clean_title"], movie.get("year"))
                except Exception:
                    pass

        if found_url:
            recommender.posters_cache[mid_str] = found_url
            try:
                from populate_all_posters import save_cache
                save_cache(recommender.posters_cache)
            except Exception:
                pass
            return redirect(found_url, code=302)

    movie = recommender.get_movie_details(movie_id)
    if not movie:
        title = "Movie Not Found"
        year_str = "----"
        genre_str = "Cinema"
        rating_str = "0.0"
        palette = ("#475569", "#0f172a", "#94a3b8")
    else:
        title = movie["clean_title"]
        year_str = str(movie["year"]) if movie["year"] else ""
        primary_genre = movie["genres"][0].lower() if movie["genres"] else "drama"
        genre_str = movie["genres"][0] if movie["genres"] else "Cinema"
        rating_str = f"{movie['rating_mean']:.1f}" if movie["rating_mean"] > 0 else "N/A"
        palette = GENRE_PALETTES.get(primary_genre, ("#6366f1", "#1e1b4b", "#818cf8"))

    c1, c2, c_accent = palette

    # Word wrap title for SVG
    words = title.split()
    lines = []
    current_line = []
    for w in words:
        if len(" ".join(current_line + [w])) <= 16:
            current_line.append(w)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
    if current_line:
        lines.append(" ".join(current_line))
    lines = lines[:4]  # max 4 lines

    # SVG text spans
    start_y = 300 - (len(lines) * 16)
    text_spans = ""
    for i, line in enumerate(lines):
        y_pos = start_y + (i * 34)
        escaped_line = html.escape(line)
        text_spans += f'<text x="200" y="{y_pos}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="26" font-weight="800" fill="#ffffff" letter-spacing="-0.5">{escaped_line}</text>\n'

    escaped_genre = html.escape(genre_str.upper())
    escaped_year = html.escape(year_str)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 600" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}" />
      <stop offset="60%" stop-color="{c2}" />
      <stop offset="100%" stop-color="#0b0f19" />
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="{c_accent}" stop-opacity="0.35" />
      <stop offset="100%" stop-color="{c_accent}" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="overlayGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#000000" stop-opacity="0.2" />
      <stop offset="50%" stop-color="#000000" stop-opacity="0.1" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0.85" />
    </linearGradient>
  </defs>

  <!-- Background Base -->
  <rect width="400" height="600" fill="url(#bgGrad)" />
  <rect width="400" height="600" fill="url(#glow)" />
  <rect width="400" height="600" fill="url(#overlayGrad)" />

  <!-- Geometric Film Vignette -->
  <circle cx="200" cy="180" r="100" fill="none" stroke="{c_accent}" stroke-width="1.5" stroke-opacity="0.25" stroke-dasharray="4,6" />
  <circle cx="200" cy="180" r="70" fill="none" stroke="#ffffff" stroke-width="1" stroke-opacity="0.15" />

  <!-- Cinema Icon Glyph -->
  <g transform="translate(176, 156)" fill="{c_accent}" opacity="0.9">
    <path d="M40 8H8C3.58 8 0 11.58 0 16v24c0 4.42 3.58 8 8 8h32c4.42 0 8-3.58 8-8V16c0-4.42-3.58-8-8-8zm-2 28l-10-6.5V26.5L38 20v16zM8 12h8v6H8v-6zm0 10h8v6H8v-6zm0 10h8v6H8v-6z"/>
  </g>

  <!-- Genre Badge -->
  <rect x="130" y="44" width="140" height="26" rx="13" fill="{c_accent}" fill-opacity="0.2" stroke="{c_accent}" stroke-width="1" stroke-opacity="0.5" />
  <text x="200" y="61" text-anchor="middle" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#ffffff" letter-spacing="2">{escaped_genre}</text>

  <!-- Title Spans -->
  {text_spans}

  <!-- Release Year Badge -->
  <text x="200" y="460" text-anchor="middle" font-family="-apple-system, sans-serif" font-size="15" font-weight="600" fill="#94a3b8" letter-spacing="1">{escaped_year}</text>

  <!-- Rating Footer Ribbon -->
  <g transform="translate(140, 500)">
    <rect width="120" height="34" rx="17" fill="#0f172a" fill-opacity="0.8" stroke="#334155" stroke-width="1" />
    <path d="M22 17l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L22 31.3 16.4 34.2l1.1-6.2-4.5-4.4 6.2-.9z" transform="translate(4, -8) scale(0.7)" fill="#fbbf24"/>
    <text x="65" y="22" text-anchor="middle" font-family="-apple-system, sans-serif" font-size="14" font-weight="700" fill="#f8fafc">{rating_str} ★</text>
  </g>

  <!-- CineMatch AI Watermark -->
  <text x="200" y="575" text-anchor="middle" font-family="-apple-system, sans-serif" font-size="10" font-weight="500" fill="#64748b" letter-spacing="2">CINEMATCH AI</text>
</svg>"""

    response = make_response(svg_content)
    response.headers["Content-Type"] = "image/svg+xml; charset=utf-8"
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


# 404 handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", message="The requested page or movie could not be found."), 404


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  CineMatch AI Server is starting...")
    print("  Open in browser: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
