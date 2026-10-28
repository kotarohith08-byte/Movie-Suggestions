"""
export_static_site.py - Builds the Standalone GitHub Pages CineMatch AI Website
==============================================================================
Generates:
1. static_data.js (embedded dataset of 560 curated movies with authentic posters)
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

# Select all Indian movies + top 500 popular MovieLens movies
indian_mids = [mid for mid in movies_df["movieId"] if mid >= 200000]
top_ml = movies_df[movies_df["movieId"] < 200000].sort_values(by="rating_count", ascending=False).head(500)["movieId"].tolist()

selected_mids = set(indian_mids + top_ml)
movies_list = []

for mid in selected_mids:
    row = movies_df[movies_df["movieId"] == mid].iloc[0]
    mid_int = int(mid)
    genres = [g.strip() for g in str(row["genres"]).split("|") if g.strip() and g != "(no genres listed)"]
    poster = posters_cache.get(str(mid_int)) or ""
    sims = [s[0] for s in top_sims.get(mid_int, [])[:8] if s[0] in selected_mids]

    movies_list.append({
        "id": mid_int,
        "title": str(row["clean_title"]),
        "year": int(row["year"]) if pd.notnull(row["year"]) else None,
        "genres": genres,
        "rating": float(row["rating_mean"]),
        "votes": int(row["rating_count"]),
        "score": float(row["weighted_score"]),
        "poster": poster,
        "sims": sims
    })

# Write static_data.js
js_content = f"const MOVIES_DATABASE = {json.dumps(movies_list, ensure_ascii=False)};\n"
with open(os.path.join(BASE_DIR, "static", "js", "static_data.js"), "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"[OK] Exported {len(movies_list)} movies with authentic posters to static/js/static_data.js")

# Touch .nojekyll
with open(os.path.join(BASE_DIR, ".nojekyll"), "w") as f:
    f.write("")
print("[OK] Created .nojekyll to disable Jekyll on GitHub Pages")
