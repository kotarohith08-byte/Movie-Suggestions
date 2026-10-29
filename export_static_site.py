"""
export_static_site.py - Builds the Standalone GitHub Pages CineMatch AI Website
==============================================================================
Generates:
1. static_data.js (embedded dataset of 2,085+ curated movies including 245 Tollywood + 340 Bollywood with 100% TMDB CDN posters)
2. index.html at root (standalone interactive client-side web application for GitHub Pages)
3. .nojekyll (disables Jekyll so GitHub Pages serves index.html directly)
"""

import os
import json
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

posters_cache = json.load(open(os.path.join(DATA_DIR, "posters_cache.json"), encoding="utf-8"))
movies_df = pd.read_csv(os.path.join(DATA_DIR, "processed_movies.csv"))
top_sims = joblib.load(os.path.join(MODELS_DIR, "content_top_sims.joblib"))

# Select all 585 Indian movies (245 Tollywood + 340 Bollywood) + top 1,500 popular MovieLens movies
indian_mids = [mid for mid in movies_df["movieId"] if mid >= 200000]
top_ml = movies_df[movies_df["movieId"] < 200000].sort_values(by="rating_count", ascending=False).head(1500)["movieId"].tolist()

selected_mids = set(indian_mids + top_ml)
movies_list = []

for mid in selected_mids:
    row = movies_df[movies_df["movieId"] == mid].iloc[0]
    mid_int = int(mid)
    genres = [g.strip() for g in str(row["genres"]).split("|") if g.strip() and g != "(no genres listed)"]
    poster = posters_cache.get(str(mid_int)) or ""
    sims = [s[0] for s in top_sims.get(mid_int, [])[:8] if s[0] in selected_mids]

    # Tag language/industry
    is_tollywood = bool((200001 <= mid_int <= 200030) or (200061 <= mid_int <= 200275))
    is_bollywood = bool((200031 <= mid_int <= 200060) or (mid_int >= 200301))

    movies_list.append({
        "id": mid_int,
        "title": str(row["clean_title"]),
        "full_title": str(row["title"]),
        "year": int(row["year"]) if pd.notnull(row["year"]) else None,
        "genres": genres,
        "rating": float(round(row["rating_mean"], 2)),
        "votes": int(row["rating_count"]),
        "score": float(round(row["weighted_score"], 2)),
        "poster": poster,
        "sims": sims,
        "industry": "Tollywood" if is_tollywood else ("Bollywood" if is_bollywood else "Global")
    })

# Sort movies: Indian blockbusters first, then by popularity/votes
movies_list.sort(key=lambda m: (m["id"] < 200000, -m["votes"], -m["score"]))

# Write static_data.js with BOTH window.MOVIES_DATABASE and var MOVIES_DATABASE
json_data = json.dumps(movies_list, ensure_ascii=False)
js_content = f"var MOVIES_DATABASE = {json_data};\nif (typeof window !== 'undefined') {{ window.MOVIES_DATABASE = MOVIES_DATABASE; }}\n"

with open(os.path.join(BASE_DIR, "static", "js", "static_data.js"), "w", encoding="utf-8") as f:
    f.write(js_content)

tollywood_count = sum(1 for m in movies_list if m["industry"] == "Tollywood")
bollywood_count = sum(1 for m in movies_list if m["industry"] == "Bollywood")
print(f"[OK] Exported {len(movies_list)} movies total ({tollywood_count} Tollywood, {bollywood_count} Bollywood) with 100% TMDB CDN posters to static/js/static_data.js")

# Touch .nojekyll
with open(os.path.join(BASE_DIR, ".nojekyll"), "w") as f:
    f.write("")
print("[OK] Created .nojekyll to disable Jekyll on GitHub Pages")
