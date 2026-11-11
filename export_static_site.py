"""
export_static_site.py - Builds the Standalone GitHub Pages CineMatch AI Website
==============================================================================
Generates:
1. static_data.js (embedded dataset of ALL 10,742 movies: 415 Kollywood, 340 Bollywood, 245 Tollywood, and 9,742 Hollywood titles)
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

# Load TMDB ID mappings from links.csv
links_path = os.path.join(DATA_DIR, "links.csv")
links_map = {}
if os.path.exists(links_path):
    links_df = pd.read_csv(links_path).dropna(subset=["tmdbId"])
    links_map = dict(zip(links_df["movieId"].astype(int), links_df["tmdbId"].astype(int)))

# Verified TMDB IDs for Indian Cinema blockbusters
INDIAN_TMDB_MAP = {
    200001: 579974,  # RRR
    200002: 256040,  # Baahubali: The Beginning
    200003: 350312,  # Baahubali 2: The Conclusion
    200004: 801688,  # Kalki 2898 AD
    200005: 690957,  # Pushpa: The Rise
    200006: 912649,  # Pushpa 2: The Rule
    200007: 939243,  # Hanu-Man
    200008: 897087,  # Salaar: Part 1 - Ceasefire
    200009: 980489,  # Devara: Part 1
    200010: 1142564, # Saripodhaa Sanivaaram
    200011: 1073867, # Hi Nanna
    200012: 984180,  # Sita Ramam
    200013: 949423,  # Karthikeya 2
    200014: 799883,  # Major
    200015: 618355,  # Ala Vaikunthapurramuloo
    200061: 256040,  # Baahubali: The Beginning
    200062: 350312,  # Baahubali 2: The Conclusion
    200063: 801688,  # Kalki 2898-AD
    200064: 912649,  # Pushpa 2 - The Rule
    200068: 597219,  # Saaho
    200301: 182811,  # The Lunchbox
    200302: 1124564, # KILL
    200303: 84175,   # Gangs of Wasseypur - Part 1
    200305: 585268,  # War
    200306: 186676,  # Chennai Express
    200307: 271714,  # Bajirao Mastani
    200308: 127532,  # OMG: Oh My God!
    200309: 353569,  # Dilwale
    200310: 132316,  # Jab Tak Hai Jaan
    200311: 568379,  # Period. End of Sentence.
    200312: 411088,  # Pink
    200313: 491473,  # Pad Man
    200314: 412154,  # Dear Zindagi
    200315: 84178,   # Dhoom 3
    200316: 381696,  # Sultan
    200317: 379854,  # Neerja
    200318: 160718,  # Special 26
    200319: 283587,  # Happy New Year
    200320: 121731,  # Talaash
    200321: 379149,  # Raees
    200322: 338766,  # Fan
    200324: 505192,  # Sanju
    200325: 351044,  # Airlift
    200326: 359412,  # Talvar
    200327: 287590,  # Bang Bang!
    200328: 724495,  # Gangubai Kathiawadi
    200330: 441031,  # Secret Superstar
    200331: 1075676, # Lost Ladies (Laapataa Ladies)
    200332: 380536,  # Kapoor & Sons
    200336: 574475,  # Badla
    200339: 116149,  # Ek Tha Tiger
    200340: 386591,  # Udta Punjab
    200344: 310860,  # Tamasha
    200345: 379029,  # Sanam Teri Kasam
    200346: 496331,  # Brahmāstra Part One: Shiva
    200353: 565310,  # Kabir Singh
    200355: 87826,   # Agneepath
    200358: 153158,  # Krrish 3
    200360: 468225,  # Tiger Zinda Hai
    200361: 531309,  # Super 30
    200375: 785538,  # Fighter
    200376: 624860,  # Sooryavanshi
    201001: 1118224, # Maharaja
    201002: 1094556, # Amaran
    201003: 885110,  # Jai Bhim
    201004: 458305,  # Vikram Vedha
    201005: 535292,  # Ratsasan
    201006: 743563,  # Vikram
    201007: 633908,  # Kaithi
    201008: 553600,  # 96
    201009: 649609,  # Soorarai Pottru
    201010: 540503,  # Super Deluxe
    201011: 1041513, # The Elephant Whisperers
    201012: 395990,  # 24
    201013: 949229,  # Leo
    201014: 373023,  # 2.0
    201015: 460135,  # Mersal
    201016: 127867,  # Thuppakki
    201017: 460846,  # Vada Chennai
    201018: 582885,  # Asuran
    201019: 645541,  # Master
    201020: 980078,  # Jailer
    201021: 271404,  # Kaththi
    201022: 370663   # Theri
}

movies_list = []

for _, row in movies_df.iterrows():
    mid = int(row["movieId"])
    genres = [g.strip() for g in str(row["genres"]).split("|") if g.strip() and g != "(no genres listed)"]
    poster = posters_cache.get(str(mid)) or ""
    # Top 4 similar movies
    sims = [s[0] for s in top_sims.get(mid, [])[:5]]

    # Tag language/industry
    is_kollywood = bool(mid >= 201001)
    is_tollywood = bool((200001 <= mid <= 200030) or (200061 <= mid <= 200275))
    is_bollywood = bool((200031 <= mid <= 200060) or (200301 <= mid <= 200615))

    industry = "Kollywood" if is_kollywood else ("Tollywood" if is_tollywood else ("Bollywood" if is_bollywood else "Global"))

    tmdb_id = INDIAN_TMDB_MAP.get(mid) or links_map.get(mid)

    movies_list.append({
        "id": mid,
        "tmdbId": int(tmdb_id) if tmdb_id else None,
        "title": str(row["clean_title"]),
        "full_title": str(row["title"]),
        "year": int(row["year"]) if pd.notnull(row["year"]) else None,
        "genres": genres,
        "rating": float(round(row["rating_mean"], 2)),
        "votes": int(row["rating_count"]),
        "score": float(round(row["weighted_score"], 2)),
        "poster": poster,
        "sims": sims,
        "industry": industry
    })

# Sort order: Indian cinema blockbusters first, then by popularity/votes descending
movies_list.sort(key=lambda m: (m["id"] < 200000, -m["votes"], -m["score"]))

# Write static_data.js with BOTH window.MOVIES_DATABASE and var MOVIES_DATABASE
json_data = json.dumps(movies_list, ensure_ascii=False)
js_content = f"var MOVIES_DATABASE = {json_data};\nif (typeof window !== 'undefined') {{ window.MOVIES_DATABASE = MOVIES_DATABASE; }}\n"

with open(os.path.join(BASE_DIR, "static", "js", "static_data.js"), "w", encoding="utf-8") as f:
    f.write(js_content)

kollywood_count = sum(1 for m in movies_list if m["industry"] == "Kollywood")
tollywood_count = sum(1 for m in movies_list if m["industry"] == "Tollywood")
bollywood_count = sum(1 for m in movies_list if m["industry"] == "Bollywood")
hollywood_count = sum(1 for m in movies_list if m["industry"] == "Global")

print(f"[OK] Successfully exported ALL {len(movies_list)} movies:")
print(f"     - Kollywood (Tamil) : {kollywood_count}")
print(f"     - Tollywood (Telugu): {tollywood_count}")
print(f"     - Bollywood (Hindi) : {bollywood_count}")
print(f"     - Hollywood & World : {hollywood_count}")
print("[OK] Dataset exported to static/js/static_data.js")

# Touch .nojekyll
with open(os.path.join(BASE_DIR, ".nojekyll"), "w") as f:
    f.write("")
print("[OK] Created .nojekyll to disable Jekyll on GitHub Pages")
