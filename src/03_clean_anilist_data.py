from pathlib import Path

import pandas as pd

#FILE PATHS

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_FOLDER = PROJECT_ROOT / "data" / "raw"
PROCESSED_FOLDER = PROJECT_ROOT / "data" / "processed"

PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)

ANIME_FILE = RAW_FOLDER / "anime_raw.csv"
CHARACTER_ROLE_FILE = (
    RAW_FOLDER / "anime_character_roles_raw.csv"
)

#LOAD RAW DATA

anime = pd.read_csv(ANIME_FILE)
relationships = pd.read_csv(CHARACTER_ROLE_FILE)

print("Raw anime rows:", len(anime))
print("Raw character appearances:", len(relationships))

#CLEAN ANIME TABLE

anime["title_display"] = (
    anime["title_english"]
    .fillna(anime["title_romaji"])
)

anime["average_score"] = pd.to_numeric(
    anime["average_score"],
    errors="coerce",
)

anime["anime_popularity"] = pd.to_numeric(
    anime["anime_popularity"],
    errors="coerce",
)

anime["anime_favourites"] = pd.to_numeric(
    anime["anime_favourites"],
    errors="coerce",
)

anime["release_year"] = pd.to_numeric(
    anime["release_year"],
    errors="coerce",
).astype("Int64")

anime_clean = (
    anime
    .drop_duplicates(subset=["anime_id"])
    .sort_values(
        "anime_popularity",
        ascending=False,
    )
    .reset_index(drop=True)
)

#CLEAN CHARACTER-ANIME RELATIONSHIPS
relationships["character_name"] = (
    relationships["character_name"]
    .str.strip()
)

relationships["character_role"] = (
    relationships["character_role"]
    .str.upper()
    .str.strip()
)

relationships["character_favourites"] = (
    pd.to_numeric(
        relationships["character_favourites"],
        errors="coerce",
    )
    .fillna(0)
    .astype(int)
)

relationships_clean = (
    relationships
    .dropna(
        subset=[
            "anime_id",
            "character_id",
            "character_name",
            "character_role",
        ]
    )
    .drop_duplicates(
        subset=["anime_id", "character_id"]
    )
    .reset_index(drop=True)
)


#CREATE ONE ROW PER UNIQUE CHARACTER
character_columns = [
    "character_id",
    "character_name",
    "character_native_name",
    "character_gender",
    "character_age",
    "character_favourites",
    "character_image_url",
    "character_url",
    "snapshot_date",
]

characters_clean = (
    relationships_clean[character_columns]
    .sort_values(
        "character_favourites",
        ascending=False,
    )
    .drop_duplicates(subset=["character_id"])
    .reset_index(drop=True)
)

#SUMMARIZE CHARACTER ROLES
def assign_canonical_role(role_series):
    """
    Give each character one overall role.

    MAIN takes priority if a character is main
    in at least one sampled anime.
    """

    roles = set(role_series.dropna())

    if "MAIN" in roles:
        return "MAIN"

    if "SUPPORTING" in roles:
        return "SUPPORTING"

    if "BACKGROUND" in roles:
        return "BACKGROUND"

    return "UNKNOWN"


character_summary = (
    relationships_clean
    .groupby("character_id")
    .agg(
        anime_appearances=(
            "anime_id",
            "nunique",
        ),
        canonical_role=(
            "character_role",
            assign_canonical_role,
        ),
        observed_roles=(
            "character_role",
            lambda values: "|".join(
                sorted(set(values))
            ),
        ),
    )
    .reset_index()
)

characters_clean = characters_clean.merge(
    character_summary,
    on="character_id",
    how="left",
)

#CREATE PRIMARY ANALYSIS TABLE
analysis_relationships = relationships_clean[
    relationships_clean["character_role"].isin(
        ["MAIN", "SUPPORTING"]
    )
].copy()

anime_fields = anime_clean[
    [
        "anime_id",
        "title_display",
        "format",
        "release_year",
        "genres",
        "average_score",
        "anime_popularity",
        "anime_favourites",
    ]
]

analysis_relationships = (
    analysis_relationships
    .drop(columns=["anime_title"])
    .merge(
        anime_fields,
        on="anime_id",
        how="left",
    )
)

#SAVE PROCESSED DATA
anime_clean.to_csv(
    PROCESSED_FOLDER / "anime_clean.csv",
    index=False,
    encoding="utf-8-sig",
)

characters_clean.to_csv(
    PROCESSED_FOLDER / "characters_clean.csv",
    index=False,
    encoding="utf-8-sig",
)

relationships_clean.to_csv(
    PROCESSED_FOLDER
    / "anime_character_roles_clean.csv",
    index=False,
    encoding="utf-8-sig",
)

analysis_relationships.to_csv(
    PROCESSED_FOLDER
    / "character_popularity_analysis.csv",
    index=False,
    encoding="utf-8-sig",
)

#QUALITY CHECK SUMMARY

print("\nCleaning complete!")
print("Clean anime:", len(anime_clean))
print("Unique characters:", len(characters_clean))

print(
    "Main/supporting analysis rows:",
    len(analysis_relationships),
)

print("\nAnalysis roles:")
print(
    analysis_relationships[
        "character_role"
    ].value_counts()
)

print(
    "\nCharacters with multiple anime appearances:",
    (
        characters_clean["anime_appearances"] > 1
    ).sum(),
)

print(
    "\nProcessed files saved to:",
    PROCESSED_FOLDER,
)