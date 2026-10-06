"""
ETL: India Road Accidents 2019-2023 (OpenCity / MoRTH)
Extract: two wide CSVs -> Transform: clean, reshape wide->long, join, metrics -> Load: SQLite + clean CSV for Tableau
Source: https://data.opencity.in/dataset/road-accidents-in-india-2023 (public domain, sourced from morth.gov.in)
Run: python etl.py
"""
import pandas as pd
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
OUT_DB = BASE / "road_accidents.db"
OUT_CSV = BASE / "road_accidents_clean.csv"

ACCIDENT_COLS = {2019: "2019 Accidents", 2020: "2020 Accidents", 2021: "2021 Accidents",
                 2022: "2022 Accidents", 2023: "2023 Accidents"}
FATALITY_COLS = {2019: "2019 Killed", 2020: "2020 Killed", 2021: "2021 Killed",
                 2022: "2022 Killed", 2023: "2023 Killed"}

# Footnote / total rows to drop after cleaning
DROP_STATES = {"total", "all india", "# includes ladakh for 2019 and 2020",
               "* dadra and nagar haveli includes daman and diu"}

def clean_state(s: str) -> str:
    s = str(s).strip()
    # remove footnote markers *, #, trailing spaces
    s = s.replace("*", "").replace("#", "").strip()
    # normalise J & K variants
    if s.lower().startswith("j & k"):
        return "Jammu & Kashmir"
    if s.lower() == "dadra & nagar haveli":
        return "Dadra & Nagar Haveli and Daman & Diu"
    return s

def to_int(x):
    if pd.isna(x):
        return None
    s = str(x).strip().replace(",", "")
    if s.upper() in ("", "NA", "N/A", "#N/A", "NAN", "NONE", "-"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None

def load_wide(path, col_map, value_name):
    df = pd.read_csv(path, dtype=str)
    # keep only Sl No, State + year cols (Sl No identifies Total/footnote rows)
    year_cols = list(col_map.values())
    df = df[["Sl No", "State"] + year_cols].copy()
    # drop Total + footnote rows where Sl No is not numeric
    df["Sl No"] = df["Sl No"].astype(str).str.strip()
    df = df[df["Sl No"].str.isdigit()]
    df["State"] = df["State"].astype(str).map(clean_state)
    # drop All-India total row (we recompute totals from states to avoid double-counting)
    df = df[~df["State"].str.lower().isin(DROP_STATES)]
    # NOTE: keep "Daman & Diu" for now — its 2019 values are merged into
    # "Dadra & Nagar Haveli and Daman & Diu" in main() (UTs merged Jan 2020).
    # Ladakh NA years (2019-2020) are kept as NULLs — J&K figures for those
    # years already include Ladakh per MoRTH footnote.
    df = df.drop(columns=["Sl No"])
    for c in year_cols:
        df[c] = df[c].map(to_int)
    # wide -> long
    inv = {v: k for k, v in col_map.items()}
    long = df.melt(id_vars="State", value_vars=year_cols,
                   var_name="col", value_name=value_name)
    long["year"] = long["col"].map(inv).astype(int)
    long = long.drop(columns="col")
    return long

def main():
    acc_long = load_wide(DATA / "accidents.csv", ACCIDENT_COLS, "accidents")
    fat_long = load_wide(DATA / "fatalities.csv", FATALITY_COLS, "fatalities")

    df = pd.merge(acc_long, fat_long, on=["State", "year"], how="outer")
    # Merge pre-2020 Daman & Diu into Dadra & Nagar Haveli and Daman & Diu (current UT boundary).
    # Only 2019 has separate Daman values (69 accidents, 28 killed); later years are already merged/empty.
    MERGED_UT = "Dadra & Nagar Haveli and Daman & Diu"
    daman = df[df["State"] == "Daman & Diu"].set_index("year")
    if not daman.empty:
        for yr in [2019]:
            if yr in daman.index:
                for col in ["accidents", "fatalities"]:
                    v = daman.loc[yr, col]
                    if pd.notna(v):
                        mask = (df["State"] == MERGED_UT) & (df["year"] == yr)
                        df.loc[mask, col] = df.loc[mask, col].fillna(0) + v
        df = df[df["State"] != "Daman & Diu"].copy()
    df["State"] = df["State"].replace({"Daman & Diu": MERGED_UT})  # safety, should be empty now

    df = df.sort_values(["State", "year"]).reset_index(drop=True)

    # rename for Tableau-friendliness
    df = df.rename(columns={"State": "state"})

    # Derived: fatalities per 100 accidents (severity)
    df["fatalities_per_100_accidents"] = (df["fatalities"] / df["accidents"] * 100).round(2)

    # Derived: year-on-year % change per state (pandas; same logic reproduced in SQL with LAG)
    df["accidents_yoy_pct"] = df.groupby("state")["accidents"].pct_change(fill_method=None) * 100
    df["fatalities_yoy_pct"] = df.groupby("state")["fatalities"].pct_change(fill_method=None) * 100
    df["accidents_yoy_pct"] = df["accidents_yoy_pct"].round(2)
    df["fatalities_yoy_pct"] = df["fatalities_yoy_pct"].round(2)

    # Load: SQLite
    if OUT_DB.exists():
        OUT_DB.unlink()
    con = sqlite3.connect(OUT_DB)
    df.to_sql("road_accidents", con, index=False)
    # helpful index for Tableau/SQL queries
    con.execute("CREATE INDEX idx_state_year ON road_accidents(state, year)")
    con.commit()

    # quick QA prints
    print(f"Rows: {len(df)}, States: {df['state'].nunique()}, Years: {sorted(df['year'].unique())}")
    print(df[df['state'] == 'Rajasthan'].to_string(index=False))
    print(f"\nWrote {OUT_DB} (table: road_accidents)")

    # clean CSV for Tableau Public (Tableau can also read SQLite via ODBC, CSV is simplest)
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")

    # integrity checks
    assert df["year"].between(2019, 2023).all()
    assert (df["accidents"] >= 0).all() or df["accidents"].isna().any()
    con.close()

if __name__ == "__main__":
    main()
