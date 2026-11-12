"""
enrich_indian_ratings.py - Fetches official TMDB ratings for all 252 verified Indian titles.
"""

import os
import json
import time
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
API_KEY = "8265bd1679663a7ea12ac168da84d2e8"

auto_map_path = os.path.join(DATA_DIR, "auto_resolved_indian_tmdb.json")
with open(auto_map_path, "r", encoding="utf-8") as f:
    auto_map = json.load(f)

credits_cache_path = os.path.join(DATA_DIR, "indian_credits_cache.json")
credits_cache = {}
if os.path.exists(credits_cache_path):
    with open(credits_cache_path, "r", encoding="utf-8") as f:
        credits_cache = json.load(f)

ratings_cache_path = os.path.join(DATA_DIR, "tmdb_ratings_cache.json")
ratings_cache = {}
if os.path.exists(ratings_cache_path):
    with open(ratings_cache_path, "r", encoding="utf-8") as f:
        ratings_cache = json.load(f)

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3)
session.mount("https://", adapter)

print(f"[*] Fetching verified TMDB details for {len(auto_map)} Indian movies...", flush=True)

success_count = 0
for idx, (mid_str, tid) in enumerate(auto_map.items()):
    tid_str = str(tid)
    # Check if already fetched with valid vote_count
    if tid_str in ratings_cache and "vote_count" in ratings_cache[tid_str]:
        r_info = ratings_cache[tid_str]
    else:
        try:
            url = f"https://api.tmdb.org/3/movie/{tid}?api_key={API_KEY}"
            resp = session.get(url, timeout=4)
            if resp.status_code == 200:
                d = resp.json()
                r_info = {
                    "tmdbId": tid,
                    "title": d.get("title"),
                    "original_title": d.get("original_title"),
                    "original_language": d.get("original_language"),
                    "release_date": d.get("release_date"),
                    "vote_average": round(float(d.get("vote_average", 0.0)), 1),
                    "vote_count": int(d.get("vote_count", 0)),
                    "popularity": round(float(d.get("popularity", 0.0)), 2),
                    "backdrop_path": f"https://image.tmdb.org/t/p/w1280{d['backdrop_path']}" if d.get("backdrop_path") else None,
                    "overview": d.get("overview") or "",
                    "runtime": f"{d['runtime'] // 60}h {d['runtime'] % 60}m" if d.get("runtime") else None
                }
                ratings_cache[tid_str] = r_info
                success_count += 1
            elif resp.status_code == 429:
                time.sleep(1.0)
                continue
            else:
                r_info = None
        except Exception as e:
            print(f"  [!] Failed for {mid_str} (TMDB {tid}): {e}", flush=True)
            r_info = None
        time.sleep(0.02)

    # Sync into credits_cache
    if r_info and mid_str in credits_cache:
        credits_cache[mid_str]["vote_average"] = r_info["vote_average"]
        credits_cache[mid_str]["vote_count"] = r_info["vote_count"]
        credits_cache[mid_str]["popularity"] = r_info["popularity"]
        if r_info.get("backdrop_path") and not credits_cache[mid_str].get("backdrop_path"):
            credits_cache[mid_str]["backdrop_path"] = r_info["backdrop_path"]
        if r_info.get("overview") and not credits_cache[mid_str].get("overview"):
            credits_cache[mid_str]["overview"] = r_info["overview"]
        if r_info.get("runtime") and not credits_cache[mid_str].get("runtime"):
            credits_cache[mid_str]["runtime"] = r_info["runtime"]

    if (idx + 1) % 25 == 0 or (idx + 1) == len(auto_map):
        print(f"  [+] Processed {idx + 1}/{len(auto_map)} movies... (New fetched: {success_count})", flush=True)

# Save both caches
with open(ratings_cache_path, "w", encoding="utf-8") as f:
    json.dump(ratings_cache, f, indent=2, ensure_ascii=False)

with open(credits_cache_path, "w", encoding="utf-8") as f:
    json.dump(credits_cache, f, indent=2, ensure_ascii=False)

print(f"[SUCCESS] Finished! Cached {len(ratings_cache)} TMDB rating records. Updated indian_credits_cache.json.", flush=True)
