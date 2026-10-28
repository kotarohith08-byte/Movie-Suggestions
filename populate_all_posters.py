"""
populate_all_posters.py - Mass Poster Resolver for Every Movie in CineMatch AI
==============================================================================
Uses TMDB API and Wikipedia REST API to resolve and cache authentic theatrical
posters for all 9,800+ movies in the catalog.
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "posters_cache.json")
LINKS_CSV = os.path.join(DATA_DIR, "links.csv")
PROCESSED_MOVIES_CSV = os.path.join(DATA_DIR, "processed_movies.csv")

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "8265bd1679663a7ea12ac168da84d2e8")


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def fetch_tmdb_poster(session, tmdb_id: int):
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
        resp = session.get(url, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        pass
    return None


def fetch_wiki_poster(session, clean_title: str):
    import urllib.parse
    slug = urllib.parse.quote(clean_title.replace(" ", "_"))
    for variant in [slug, f"{slug}_(film)", f"{slug}_(movie)"]:
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{variant}"
            resp = session.get(url, headers={"User-Agent": "CineMatchAI/1.0"}, timeout=3.5)
            if resp.status_code == 200:
                thumb = resp.json().get("thumbnail")
                if thumb and "source" in thumb:
                    src = thumb["source"]
                    if "icon" not in src.lower() and "disambig" not in src.lower():
                        return src
        except Exception:
            continue
    return None


def mass_populate(limit: int = 1500, max_workers: int = 12):
    cache = load_cache()
    print(f"[*] Starting mass poster resolution. Initial cached: {len([v for v in cache.values() if v])}")

    # Load mappings
    links_df = pd.read_csv(LINKS_CSV)
    links_df = links_df.dropna(subset=["movieId", "tmdbId"]).copy()
    tmdb_map = dict(zip(links_df["movieId"].astype(int), links_df["tmdbId"].astype(int)))

    movies_df = pd.read_csv(PROCESSED_MOVIES_CSV)
    # Sort movies by rating count & Bayesian score to prioritize top viewed/rated movies first
    movies_df["rank"] = movies_df["rating_count"] * (movies_df["weighted_score"] ** 1.5)
    sorted_movies = movies_df.sort_values(by="rank", ascending=False)

    pending = []
    for _, row in sorted_movies.iterrows():
        mid = int(row["movieId"])
        mid_str = str(mid)
        if mid_str not in cache or not cache[mid_str]:
            pending.append({
                "movieId": mid,
                "tmdbId": tmdb_map.get(mid),
                "clean_title": row["clean_title"],
                "year": int(row["year"]) if pd.notnull(row["year"]) else None
            })
        if len(pending) >= limit:
            break

    print(f"[*] Resolving posters for {len(pending)} pending movies using {max_workers} concurrent threads...")
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=max_workers, pool_maxsize=max_workers)
    session.mount("https://", adapter)

    def worker(item):
        mid_str = str(item["movieId"])
        poster_url = None
        
        # 1. Try TMDB
        if item["tmdbId"]:
            poster_url = fetch_tmdb_poster(session, item["tmdbId"])

        # 2. Try Wikipedia
        if not poster_url:
            poster_url = fetch_wiki_poster(session, item["clean_title"])

        return mid_str, poster_url

    resolved = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, item): item for item in pending}
        for future in as_completed(futures):
            mid_str, poster_url = future.result()
            if poster_url:
                cache[mid_str] = poster_url
                resolved += 1
            if resolved > 0 and resolved % 50 == 0:
                save_cache(cache)
                sys.stdout.write(f"\r--> Resolved {resolved} new posters...")
                sys.stdout.flush()

    save_cache(cache)
    total_valid = len([v for v in cache.values() if v])
    print(f"\n[OK] Mass resolution complete! Added {resolved} new posters. Total authentic posters cached: {total_valid}")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    mass_populate(limit=count)
