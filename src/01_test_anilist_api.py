import requests
import pandas as pd

API_URL = "https://graphql.anilist.co"

query = """
query {
  Page(page: 1, perPage: 5) {
    media(
      type: ANIME
      sort: POPULARITY_DESC
      isAdult: false
    ) {
      id
      title {
        romaji
        english
      }
      format
      seasonYear
      averageScore
      popularity
      favourites
    }
  }
}
"""

response = requests.post(
    API_URL,
    json={"query": query},
    timeout=30
)

response.raise_for_status()

anime_list = response.json()["data"]["Page"]["media"]

rows = []

for anime in anime_list:
    rows.append(
        {
            "anime_id": anime["id"],
            "title_romaji": anime["title"]["romaji"],
            "title_english": anime["title"]["english"],
            "format": anime["format"],
            "release_year": anime["seasonYear"],
            "average_score": anime["averageScore"],
            "anime_popularity": anime["popularity"],
            "anime_favourites": anime["favourites"],
        }
    )

df = pd.DataFrame(rows)

print(df.to_string(index=False))

df.to_csv(
    "data/raw/anilist_test_sample.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nSuccess! Test data saved to data/raw/anilist_test_sample.csv")