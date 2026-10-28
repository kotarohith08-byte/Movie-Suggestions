"""
fetch_posters.py - Authentic Movie Poster Fetcher and Cache
===========================================================
Fetches authentic, high-quality movie posters from open sources:
1. Wikipedia / Wikimedia REST API (100% free, no API key required)
2. The Movie Database (TMDB) if TMDB_API_KEY environment variable is set
3. Caches poster URLs locally in data/posters_cache.json
"""

import os
import sys
import ssl
import json
import re
import urllib.request
import urllib.parse
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "posters_cache.json")
PROCESSED_MOVIES_CSV = os.path.join(DATA_DIR, "processed_movies.csv")
LINKS_CSV = os.path.join(DATA_DIR, "links.csv")


def load_posters_cache() -> dict:
    """Loads existing posters cache dictionary."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_posters_cache(cache: dict):
    """Saves posters cache dictionary to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def clean_title_for_wiki(clean_title: str, year: int = None) -> list:
    """
    Generates prioritized Wikipedia article title candidates.
    e.g. 'The Matrix' -> ['The_Matrix', 'The_Matrix_(film)']
         'Toy Story' -> ['Toy_Story', 'Toy_Story_(film)']
    """
    title = clean_title.strip()
    match = re.match(r"^(.*?),\s*(The|A|An)$", title, re.IGNORECASE)
    if match:
        title = f"{match.group(2)} {match.group(1)}"

    slug_title = urllib.parse.quote(title.replace(" ", "_"))
    
    candidates = [slug_title]
    if year:
        candidates.append(f"{slug_title}_({year}_film)")
    candidates.append(f"{slug_title}_(film)")
    candidates.append(f"{slug_title}_(movie)")

    return candidates


def fetch_poster_from_wikipedia(clean_title: str, year: int = None, timeout: int = 4) -> str:
    """
    Queries Wikipedia REST API for the official film summary thumbnail.
    Returns URL string or None.
    """
    candidates = clean_title_for_wiki(clean_title, year)
    ssl_ctx = ssl._create_unverified_context()

    for slug in candidates:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CineMatchAI/1.0 (Educational Recommendation System)"}
            )
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    thumbnail = data.get("thumbnail")
                    if thumbnail and "source" in thumbnail:
                        src = thumbnail["source"]
                        if "icon" not in src.lower() and "disambig" not in src.lower():
                            return src
        except Exception:
            continue

    return None


def fetch_poster_from_tmdb(tmdb_id: int, api_key: str, timeout: int = 4) -> str:
    """
    Fetches official poster from TMDB if API key is provided.
    """
    if not api_key or not tmdb_id:
        return None
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
    ssl_ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            poster_path = data.get("poster_path")
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        pass
    return None


def prefetch_popular_posters(limit: int = 150):
    """
    Prefetches and caches authentic posters for the top movies
    (sorted by rating count and Bayesian weighted quality).
    """
    if not os.path.exists(PROCESSED_MOVIES_CSV):
        print("[!] processed_movies.csv not found.")
        return

    movies_df = pd.read_csv(PROCESSED_MOVIES_CSV)
    cache = load_posters_cache()
    tmdb_key = os.environ.get("TMDB_API_KEY", "")

    tmdb_map = {}
    if os.path.exists(LINKS_CSV):
        try:
            links_df = pd.read_csv(LINKS_CSV)
            links_df = links_df.dropna(subset=["movieId", "tmdbId"]).copy()
            tmdb_map = dict(zip(links_df["movieId"].astype(int), links_df["tmdbId"].astype(int)))
        except Exception:
            pass

    movies_df["pop_rank"] = movies_df["rating_count"] * (movies_df["weighted_score"] ** 1.5)
    top_movies = movies_df.sort_values(by="pop_rank", ascending=False).head(limit)

    print(f"[*] Prefetching authentic posters for top {limit} movies...")
    fetched_count = 0
    already_cached = 0

    for idx, row in top_movies.iterrows():
        mid_str = str(int(row["movieId"]))
        if mid_str in cache and cache[mid_str]:
            already_cached += 1
            continue

        clean_t = row["clean_title"]
        year = int(row["year"]) if pd.notnull(row["year"]) else None
        poster_url = None

        if tmdb_key and int(row["movieId"]) in tmdb_map:
            poster_url = fetch_poster_from_tmdb(tmdb_map[int(row["movieId"])], tmdb_key)

        if not poster_url:
            poster_url = fetch_poster_from_wikipedia(clean_t, year)

        if poster_url:
            cache[mid_str] = poster_url
            fetched_count += 1
            print(f"  [+] #{mid_str} {clean_t} -> {poster_url[:65]}...")
        else:
            cache[mid_str] = None

        if (fetched_count + already_cached) % 20 == 0:
            save_posters_cache(cache)

    save_posters_cache(cache)
    valid_posters = len([v for v in cache.values() if v])
    print(f"\n[OK] Posters cache updated. Total authentic posters cached: {valid_posters}")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    prefetch_popular_posters(limit=count)
