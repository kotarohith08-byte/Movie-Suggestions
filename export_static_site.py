"""
export_static_site.py - Builds the Standalone GitHub Pages CineMatch AI Website
==============================================================================
Generates:
1. static_data.js (embedded dataset of ALL 10,327 movies in the catalog: 245 Tollywood, 340 Bollywood, and 9,742 Hollywood & World Cinema titles)
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

movies_list = []

for _, row in movies_df.iterrows():
    mid = int(row["movieId"])
    genres = [g.strip() for g in str(row["genres"]).split("|") if g.strip() and g != "(no genres listed)"]
    poster = posters_cache.get(str(mid)) or ""
    # Top 4 similar movies
    sims = [s[0] for s in top_sims.get(mid, [])[:5]]

    # Tag language/industry
    is_tollywood = bool((200001 <= mid <= 200030) or (200061 <= mid <= 200275))
    is_bollywood = bool((200031 <= mid <= 200060) or (mid >= 200301))

    movies_list.append({
        "id": mid,
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

# Sort order: Indian cinema blockbusters first, then by popularity/votes descending
movies_list.sort(key=lambda m: (m["id"] < 200000, -m["votes"], -m["score"]))

# Write static_data.js with BOTH window.MOVIES_DATABASE and var MOVIES_DATABASE
json_data = json.dumps(movies_list, ensure_ascii=False)
js_content = f"var MOVIES_DATABASE = {json_data};\nif (typeof window !== 'undefined') {{ window.MOVIES_DATABASE = MOVIES_DATABASE; }}\n"

with open(os.path.join(BASE_DIR, "static", "js", "static_data.js"), "w", encoding="utf-8") as f:
    f.write(js_content)

tollywood_count = sum(1 for m in movies_list if m["industry"] == "Tollywood")
bollywood_count = sum(1 for m in movies_list if m["industry"] == "Bollywood")
hollywood_count = sum(1 for m in movies_list if m["industry"] == "Global")

print(f"[OK] Successfully exported ALL {len(movies_list)} movies:")
print(f"     - Tollywood (Telugu): {tollywood_count}")
print(f"     - Bollywood (Hindi) : {bollywood_count}")
print(f"     - Hollywood & World : {hollywood_count}")
print("[OK] Dataset exported to static/js/static_data.js")

# Touch .nojekyll
with open(os.path.join(BASE_DIR, ".nojekyll"), "w") as f:
    f.write("")
print("[OK] Created .nojekyll to disable Jekyll on GitHub Pages")
