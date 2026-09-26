import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

#SETTINGS

API_URL = "https://graphql.anilist.co"

TOP_ANIME_COUNT = 250
ANIME_PER_PAGE = 50
CHARACTERS_PER_PAGE = 50

SNAPSHOT_DATE = date.today().isoformat()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_FOLDER = PROJECT_ROOT / "data" / "raw"

RAW_DATA_FOLDER.mkdir(parents=True, exist_ok=True)


#GRAPHQL QUERIES

ANIME_QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      currentPage
      hasNextPage
    }

    media(
      type: ANIME
      sort: POPULARITY_DESC
      isAdult: false
    ) {
      id

      title {
        romaji
        english
        native
      }

      format
      status
      season
      seasonYear
      episodes
      duration
      genres
      averageScore
      popularity
      favourites
      countryOfOrigin
      source
      siteUrl
    }
  }
}
"""


CHARACTER_QUERY = """
query ($mediaId: Int, $page: Int, $perPage: Int) {
  Media(id: $mediaId, type: ANIME) {
    characters(
      page: $page
      perPage: $perPage
    ) {
      pageInfo {
        currentPage
        hasNextPage
      }

      edges {
        role

        node {
          id

          name {
            full
            native
          }

          gender
          age
          favourites

          image {
            large
          }

          siteUrl
        }
      }
    }
  }
}
"""

#API REQUEST FUNCTION
def run_query(query, variables, max_retries=5):
    """
    Send a GraphQL query to AniList.

    If AniList temporarily rejects the request or reaches
    its rate limit, wait and try again.
    """

    for attempt in range(max_retries):
        response = requests.post(
            API_URL,
            json={
                "query": query,
                "variables": variables,
            },
            timeout=60,
        )

        if response.status_code == 200:
            response_data = response.json()

            if "errors" in response_data:
                raise RuntimeError(
                    f"AniList returned a GraphQL error: "
                    f"{response_data['errors']}"
                )

            return response_data["data"]

        if response.status_code == 429:
            wait_time = int(
                response.headers.get("Retry-After", 60)
            )

            print(
                f"Rate limit reached. "
                f"Waiting {wait_time} seconds..."
            )

            time.sleep(wait_time)
            continue

        print(
            f"Request failed with status "
            f"{response.status_code}."
        )

        time.sleep(5)

    raise RuntimeError(
        "The request failed after several attempts."
    )

#EXTRACT ANIME

def extract_anime():
    anime_rows = []

    total_pages = (
        TOP_ANIME_COUNT // ANIME_PER_PAGE
    )

    for page in range(1, total_pages + 1):
        print(
            f"Downloading anime page "
            f"{page} of {total_pages}..."
        )

        data = run_query(
            ANIME_QUERY,
            {
                "page": page,
                "perPage": ANIME_PER_PAGE,
            },
        )

        anime_list = data["Page"]["media"]

        for anime in anime_list:
            anime_rows.append(
                {
                    "anime_id": anime["id"],
                    "title_romaji": anime["title"]["romaji"],
                    "title_english": anime["title"]["english"],
                    "title_native": anime["title"]["native"],
                    "format": anime["format"],
                    "status": anime["status"],
                    "season": anime["season"],
                    "release_year": anime["seasonYear"],
                    "episodes": anime["episodes"],
                    "duration_minutes": anime["duration"],
                    "genres": "|".join(anime["genres"]),
                    "average_score": anime["averageScore"],
                    "anime_popularity": anime["popularity"],
                    "anime_favourites": anime["favourites"],
                    "country_of_origin": anime["countryOfOrigin"],
                    "source": anime["source"],
                    "anime_url": anime["siteUrl"],
                    "snapshot_date": SNAPSHOT_DATE,
                }
            )

        time.sleep(1)

    return pd.DataFrame(anime_rows)

#EXTRACT CHARACTERS
def extract_characters(anime_df):
    character_rows = []

    total_anime = len(anime_df)

    for anime_number, anime in anime_df.iterrows():
        anime_id = int(anime["anime_id"])
        anime_title = anime["title_english"]

        if pd.isna(anime_title):
            anime_title = anime["title_romaji"]

        print(
            f"[{anime_number + 1}/{total_anime}] "
            f"Downloading characters from "
            f"{anime_title}..."
        )

        character_page = 1
        has_next_page = True

        while has_next_page:
            data = run_query(
                CHARACTER_QUERY,
                {
                    "mediaId": anime_id,
                    "page": character_page,
                    "perPage": CHARACTERS_PER_PAGE,
                },
            )

            connection = data["Media"]["characters"]

            for edge in connection["edges"]:
                character = edge["node"]

                character_rows.append(
                    {
                        "anime_id": anime_id,
                        "anime_title": anime_title,
                        "character_id": character["id"],
                        "character_name": (
                            character["name"]["full"]
                        ),
                        "character_native_name": (
                            character["name"]["native"]
                        ),
                        "character_role": edge["role"],
                        "character_gender": character["gender"],
                        "character_age": character["age"],
                        "character_favourites": (
                            character["favourites"]
                        ),
                        "character_image_url": (
                            character["image"]["large"]
                        ),
                        "character_url": character["siteUrl"],
                        "snapshot_date": SNAPSHOT_DATE,
                    }
                )

            has_next_page = (
                connection["pageInfo"]["hasNextPage"]
            )

            character_page += 1

            # Pause to not overload
            time.sleep(1.2)

    return pd.DataFrame(character_rows)

#RUN EXTRACTION

def main():
    print("\nStarting AniList data extraction...")
    print(f"Snapshot date: {SNAPSHOT_DATE}\n")

    anime_df = extract_anime()

    anime_output = (
        RAW_DATA_FOLDER / "anime_raw.csv"
    )

    anime_df.to_csv(
        anime_output,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"\nSaved {len(anime_df):,} anime "
        f"to {anime_output}\n"
    )

    character_df = extract_characters(anime_df)

    character_output = (
        RAW_DATA_FOLDER
        / "anime_character_roles_raw.csv"
    )

    character_df.to_csv(
        character_output,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"\nSaved {len(character_df):,} "
        f"anime-character relationships "
        f"to {character_output}"
    )

    print("\nExtraction complete!")


if __name__ == "__main__":
    main()
    