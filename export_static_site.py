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
    200006: 857598,  # Pushpa 2: The Rule
    200007: 869760,  # Hanu-Man
    200008: 770906,  # Salaar: Part 1 - Ceasefire
    200009: 811941,  # Devara: Part 1
    200010: 1194915, # Saripodhaa Sanivaaram
    200011: 1068452, # Hi Nanna
    200012: 894803,  # Sita Ramam
    200013: 894762,  # Karthikeya 2
    200014: 605153,  # Major
    200015: 628241,  # Ala Vaikunthapurramuloo
    200016: 592898,  # Jersey
    200019: 461126,  # Rangasthalam
    200020: 459713,  # Mahanati
    200023: 473234,  # Arjun Reddy
    200024: 467649,  # Fidaa
    200025: 148265,  # Eega
    200031: 1163258, # 12th Fail
    200032: 872906,  # Jawan
    200033: 864692,  # Pathaan
    200034: 781732,  # Animal
    200035: 1112426, # Stree 2
    200036: 533991,  # Stree
    200037: 496331,  # Brahmāstra: Part One – Shiva
    200038: 352173,  # Drishyam
    200039: 1029827, # Drishyam 2
    200040: 538858,  # Tumbbad
    200041: 534780,  # Andhadhun
    200042: 547654,  # Badhaai Ho
    200043: 597089,  # Article 15
    200044: 554600,  # Uri: The Surgical Strike
    200045: 491625,  # Gully Boy
    200046: 596650,  # Chhichhore
    200047: 599925,  # Shershaah
    200048: 598826,  # Sardar Udham
    200049: 360814,  # Dangal
    200050: 348892,  # Bajrangi Bhaijaan
    200051: 297222,  # PK
    200052: 247645,  # Queen
    200053: 280795,  # Haider
    200054: 117691,  # Gangs of Wasseypur
    200055: 127501,  # Barfi!
    200056: 82825,   # Kahaani
    200057: 206324,  # Bhaag Milkha Bhaag
    200058: 185008,  # Yeh Jawaani Hai Deewani
    200059: 432527,  # Padmaavat
    200060: 491629,  # Raazi
    200061: 256040,  # Baahubali: The Beginning
    200062: 350312,  # Baahubali 2: The Conclusion
    200063: 801688,  # Kalki 2898-AD
    200064: 857598,  # Pushpa 2 - The Rule
    200068: 454292,  # Saaho
    200301: 191714,  # The Lunchbox
    200302: 1160018, # KILL
    200303: 117691,  # Gangs of Wasseypur - Part 1
    200305: 585268,  # War
    200306: 205022,  # Chennai Express
    200307: 362045,  # Bajirao Mastani
    200308: 135718,  # OMG: Oh My God!
    200309: 370665,  # Dilwale
    200310: 132316,  # Jab Tak Hai Jaan
    200311: 524288,  # Period. End of Sentence.
    200312: 415358,  # Pink
    200313: 447856,  # Pad Man
    200314: 413543,  # Dear Zindagi
    200315: 44977,   # Dhoom 3
    200316: 376812,  # Sultan
    200317: 376869,  # Neerja
    200318: 165904,  # Special 26
    200319: 277432,  # Happy New Year
    200320: 86004,   # Talaash
    200321: 363343,  # Raees
    200322: 377985,  # Fan
    200324: 496328,  # Sanju
    200325: 375290,  # Airlift
    200326: 353464,  # Talvar
    200327: 283589,  # Bang Bang!
    200328: 664332,  # Gangubai Kathiawadi
    200330: 441889,  # Secret Superstar
    200331: 1163194, # Lost Ladies (Laapataa Ladies)
    200332: 374173,  # Kapoor & Sons
    200336: 581361,  # Badla
    200339: 85985,   # Ek Tha Tiger
    200340: 398535,  # Udta Punjab
    200344: 339274,  # Tamasha
    200345: 381418,  # Sanam Teri Kasam
    200346: 496331,  # Brahmāstra Part One: Shiva
    200353: 577328,  # Kabir Singh
    200355: 84858,   # Agneepath
    200358: 204435,  # Krrish 3
    200360: 441909,  # Tiger Zinda Hai
    200361: 534075,  # Super 30
    201001: 1118224, # Maharaja
    201002: 927342,  # Amaran
    201003: 855400,  # Jai Bhim
    201004: 432139,  # Vikram Vedha
    201005: 412862,  # Ratsasan
    201006: 743563,  # Vikram
    201007: 587030,  # Kaithi
    201008: 441717,  # 96
    201009: 595228,  # Soorarai Pottru
    201010: 432011,  # Super Deluxe
    201011: 1041580, # The Elephant Whisperers
    201012: 368006,  # 24
    201013: 949229,  # Leo
    201014: 373449,  # 2.0
    201015: 456287,  # Mersal
    201016: 143010,  # Thuppakki
    201017: 410331,  # Vada Chennai
    201018: 576928,  # Asuran
    201019: 626392,  # Master
    201020: 937020,  # Jailer
    201021: 263475,  # Kaththi
    201022: 370076,  # Theri
    201025: 660046,  # Ponniyin Selvan: Part I
    201069: 858082   # Ponniyin Selvan: Part II
}

# Merge all auto-resolved Indian TMDB IDs
auto_resolved_path = os.path.join(DATA_DIR, "auto_resolved_indian_tmdb.json")
if os.path.exists(auto_resolved_path):
    with open(auto_resolved_path, "r", encoding="utf-8") as f:
        auto_map = json.load(f)
        for k, v in auto_map.items():
            INDIAN_TMDB_MAP[int(k)] = int(v)

# Load prebaked Indian credits cache
indian_credits_cache = {}
credits_cache_path = os.path.join(DATA_DIR, "indian_credits_cache.json")
if os.path.exists(credits_cache_path):
    with open(credits_cache_path, "r", encoding="utf-8") as f:
        indian_credits_cache = json.load(f)


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

# Write static_data.js with BOTH window.MOVIES_DATABASE and window.PREBAKED_INDIAN_CREDITS
json_data = json.dumps(movies_list, ensure_ascii=False)
credits_json = json.dumps(indian_credits_cache, ensure_ascii=False)
js_content = (
    f"var MOVIES_DATABASE = {json_data};\n"
    f"if (typeof window !== 'undefined') {{ window.MOVIES_DATABASE = MOVIES_DATABASE; }}\n\n"
    f"var PREBAKED_INDIAN_CREDITS = {credits_json};\n"
    f"if (typeof window !== 'undefined') {{ window.PREBAKED_INDIAN_CREDITS = PREBAKED_INDIAN_CREDITS; }}\n"
)

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
