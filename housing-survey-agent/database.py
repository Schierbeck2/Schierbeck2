"""Database layer for the manufactured housing property database.

Connects to PostgreSQL to:
- Query properties by county, radius, or proximity to a subject property
- Look up phone numbers for properties
- Write survey results to the rent table

Table/column names use reasonable defaults. Adjust to match your
actual schema by editing the TABLE/COLUMN constants below, or by
setting them in environment variables.
"""

import math
import os
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Table & column name configuration
# Override these via env vars if your schema uses different names.
# ---------------------------------------------------------------------------
PROPERTY_TABLE = os.environ.get("MH_PROPERTY_TABLE", "properties")
RENT_TABLE = os.environ.get("MH_RENT_TABLE", "rent_surveys")

# Property table columns
COL_PROPERTY_ID = os.environ.get("MH_COL_PROPERTY_ID", "property_id")
COL_NAME = os.environ.get("MH_COL_NAME", "property_name")
COL_ADDRESS = os.environ.get("MH_COL_ADDRESS", "address")
COL_CITY = os.environ.get("MH_COL_CITY", "city")
COL_STATE = os.environ.get("MH_COL_STATE", "state")
COL_COUNTY = os.environ.get("MH_COL_COUNTY", "county")
COL_ZIP = os.environ.get("MH_COL_ZIP", "zip_code")
COL_PHONE = os.environ.get("MH_COL_PHONE", "phone")
COL_LAT = os.environ.get("MH_COL_LAT", "latitude")
COL_LNG = os.environ.get("MH_COL_LNG", "longitude")
COL_TOTAL_LOTS = os.environ.get("MH_COL_TOTAL_LOTS", "total_lots")


def get_connection():
    """Create a database connection from environment variables."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "mh_properties"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
    )


# ---------------------------------------------------------------------------
# Property lookups
# ---------------------------------------------------------------------------

def get_property_by_id(property_id: int) -> dict | None:
    """Fetch a single property by ID."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM {PROPERTY_TABLE} WHERE {COL_PROPERTY_ID} = %s",
                (property_id,),
            )
            return dict(cur.fetchone()) if cur.rowcount else None
    finally:
        conn.close()


def get_properties_by_county(county: str, state: str) -> list[dict]:
    """Fetch all properties in a given county and state."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT * FROM {PROPERTY_TABLE}
                    WHERE UPPER({COL_COUNTY}) = UPPER(%s)
                      AND UPPER({COL_STATE}) = UPPER(%s)
                    ORDER BY {COL_NAME}""",
                (county, state),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_properties_by_radius(
    lat: float, lng: float, radius_miles: float = 10.0
) -> list[dict]:
    """Fetch all properties within a radius of a lat/lng point.

    Uses the Haversine formula in SQL for distance calculation.
    Returns results sorted by distance (nearest first).
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Haversine formula in SQL (miles)
            cur.execute(
                f"""SELECT *,
                    (3959 * acos(
                        cos(radians(%s)) * cos(radians({COL_LAT}))
                        * cos(radians({COL_LNG}) - radians(%s))
                        + sin(radians(%s)) * sin(radians({COL_LAT}))
                    )) AS distance_miles
                FROM {PROPERTY_TABLE}
                WHERE {COL_LAT} IS NOT NULL
                  AND {COL_LNG} IS NOT NULL
                HAVING distance_miles <= %s
                ORDER BY distance_miles""",
                (lat, lng, lat, radius_miles),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def find_survey_targets(
    subject_property_id: int,
    radius_miles: float = 10.0,
    include_county: bool = True,
) -> list[dict]:
    """Given a subject property you're appraising, find all nearby MH
    communities to survey.

    Combines radius search with county match to cast a wide net,
    then deduplicates. Excludes the subject property itself.
    """
    subject = get_property_by_id(subject_property_id)
    if not subject:
        raise ValueError(f"Property {subject_property_id} not found")

    results = {}

    # Radius search
    lat = subject.get(COL_LAT)
    lng = subject.get(COL_LNG)
    if lat and lng:
        for prop in get_properties_by_radius(lat, lng, radius_miles):
            pid = prop[COL_PROPERTY_ID]
            if pid != subject_property_id:
                results[pid] = prop

    # County search
    if include_county:
        county = subject.get(COL_COUNTY)
        state = subject.get(COL_STATE)
        if county and state:
            for prop in get_properties_by_county(county, state):
                pid = prop[COL_PROPERTY_ID]
                if pid != subject_property_id and pid not in results:
                    results[pid] = prop

    return list(results.values())


# ---------------------------------------------------------------------------
# Rent survey results
# ---------------------------------------------------------------------------

def ensure_rent_table():
    """Create the rent survey table if it doesn't exist.

    This is the default schema - adjust to match your actual rent table.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {RENT_TABLE} (
                    survey_id SERIAL PRIMARY KEY,
                    {COL_PROPERTY_ID} INTEGER REFERENCES {PROPERTY_TABLE}({COL_PROPERTY_ID}),
                    survey_date TIMESTAMP DEFAULT NOW(),

                    -- Contact
                    contact_name TEXT,
                    contact_title TEXT,

                    -- Occupancy
                    total_lots INTEGER,
                    occupied_lots INTEGER,
                    occupancy_rate NUMERIC(5,4),

                    -- Rent
                    lot_rent_min NUMERIC(10,2),
                    lot_rent_max NUMERIC(10,2),
                    lot_rent_average NUMERIC(10,2),

                    -- Utilities & fees
                    utilities_included TEXT,
                    additional_fees TEXT,
                    water_sewer_cost TEXT,
                    trash_cost TEXT,

                    -- Community details
                    pet_policy TEXT,
                    age_restriction TEXT,
                    home_sales_on_site BOOLEAN,
                    rent_increase_history TEXT,
                    recent_rent_increase TEXT,
                    waitlist BOOLEAN,

                    -- Call metadata
                    call_recording_url TEXT,
                    call_duration_seconds INTEGER,
                    call_quality_score NUMERIC(3,2),
                    auto_approved BOOLEAN DEFAULT FALSE,
                    reviewed BOOLEAN DEFAULT FALSE,

                    -- Raw data
                    conversation_json JSONB,
                    notes TEXT
                )
            """)
            conn.commit()
    finally:
        conn.close()


def save_survey_to_db(property_id: int, survey_data: dict, conversation: list[dict],
                      call_metadata: dict | None = None) -> int:
    """Write a completed survey to the rent table.

    Returns the new survey_id.
    """
    import json

    meta = call_metadata or {}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {RENT_TABLE} (
                        {COL_PROPERTY_ID}, survey_date,
                        contact_name, contact_title,
                        total_lots, occupied_lots, occupancy_rate,
                        lot_rent_min, lot_rent_max, lot_rent_average,
                        utilities_included, additional_fees,
                        water_sewer_cost, trash_cost,
                        pet_policy, age_restriction,
                        home_sales_on_site, rent_increase_history,
                        recent_rent_increase, waitlist,
                        call_recording_url, call_duration_seconds,
                        call_quality_score, auto_approved,
                        conversation_json, notes
                    ) VALUES (
                        %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s
                    ) RETURNING survey_id""",
                (
                    property_id, datetime.now(),
                    survey_data.get("contact_name"), survey_data.get("contact_title"),
                    survey_data.get("total_lots"), survey_data.get("occupied_lots"),
                    survey_data.get("occupancy_rate"),
                    survey_data.get("lot_rent_min"), survey_data.get("lot_rent_max"),
                    survey_data.get("lot_rent_average"),
                    survey_data.get("utilities_included"), survey_data.get("additional_fees"),
                    survey_data.get("water_sewer_cost"), survey_data.get("trash_cost"),
                    survey_data.get("pet_policy"), survey_data.get("age_restriction"),
                    survey_data.get("home_sales_on_site"), survey_data.get("rent_increase_history"),
                    survey_data.get("recent_rent_increase"), survey_data.get("waitlist"),
                    meta.get("recording_url"), meta.get("duration_seconds"),
                    meta.get("quality_score"), meta.get("auto_approved", False),
                    json.dumps(conversation), survey_data.get("notes"),
                ),
            )
            survey_id = cur.fetchone()[0]
            conn.commit()
            return survey_id
    finally:
        conn.close()


def get_recent_surveys(property_id: int, limit: int = 5) -> list[dict]:
    """Check if a property has been surveyed recently (to avoid repeat calls)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT * FROM {RENT_TABLE}
                    WHERE {COL_PROPERTY_ID} = %s
                    ORDER BY survey_date DESC
                    LIMIT %s""",
                (property_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
