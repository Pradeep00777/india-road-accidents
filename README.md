# India Road Accidents 2019–2023 — ETL + SQL + Tableau

State-wise road accidents and fatalities (2019–2023) with a focus on **Rajasthan**. Built for a data-analyst portfolio: Python ETL → SQLite → SQL window functions → Tableau Public dashboard.

## Data source
- OpenCity dataset “Road Accidents in India 2023” (public domain, sourced from MoRTH / `morth.gov.in`):
  - State-wise accidents 2019–2023
  - State-wise fatalities (“Killed”) 2019–2023
- Raw CSVs: `data/accidents.csv`, `data/fatalities.csv`
- License: public domain (OpenCity lists “Other (Public Domain)”). Cite MoRTH + OpenCity in dashboard.

## What the ETL does (`etl.py`)
1. **Extract:** loads both wide CSVs with pandas.
2. **Transform:**
   - drops All-India total + footnote rows (keeps recomputed totals to avoid double-counting),
   - cleans state names (`J & K #` → `Jammu & Kashmir`, `Dadra & Nagar Haveli*` → `Dadra & Nagar Haveli and Daman & Diu`),
   - merges pre-2020 **Daman & Diu** (69 accidents / 28 killed in 2019) into Dadra & Nagar Haveli and Daman & Diu (UTs merged Jan 2020),
   - keeps **Ladakh** NULLs for 2019–2020 (MoRTH footnote: J&K figures already include Ladakh those years),
   - strips Indian thousands commas (`"7,984"` → `7984`), coerces `NA`/`#N/A`/empty → NULL,
   - reshapes wide → long (`state, year, accidents, fatalities`),
   - joins accidents + fatalities, computes **fatalities per 100 accidents** and **YoY % change**.
3. **Load:** writes `road_accidents.db` (table `road_accidents`, 180 rows = 36 states/UTs × 5 years) + `road_accidents_clean.csv` for Tableau Public.

Run:
```bash
pip install -r requirements.txt
python etl.py
```

Validation: summed state totals from the cleaned DB match official All-India figures exactly (e.g. 2019: 456,959 accidents / 158,984 killed; 2023: 480,583 / 172,890).

## SQL (`queries.sql`)
SQLite-compatible, 8 queries. Highlights:
- Q1–Q3: 2023 rankings with `RANK()` (accidents, fatalities, severity).
- Q4–Q6: `LAG()` YoY for Rajasthan, Rajasthan rank per year (CTE — filter *after* ranking), all-India COVID dip/rebound.
- Q7: 3-year moving average with `AVG() OVER (... ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)`.

Run:
```bash
sqlite3 road_accidents.db < queries.sql
```

## Findings (from the cleaned data — use these exact numbers)
- **All-India:** 456,959 accidents (2019) → 372,181 in 2020 (**−18.6%**, COVID) → 412,432 → 461,312 → **480,583 in 2023 (5-year high)**. Fatalities: 158,984 → 138,383 → 153,972 → 168,491 → **172,890 in 2023 (5-year high)**.
- **2023 volume leaders:** accidents — Tamil Nadu (67,213), Madhya Pradesh (55,327), Kerala (48,091); fatalities — Uttar Pradesh (23,652), Tamil Nadu (18,347), Maharashtra (15,366).
- **2023 severity** (fatalities per 100 accidents, states ≥1,000 accidents): Bihar **80.6**, Jharkhand 78.5, Punjab 77.0, Uttarakhand 62.3, UP 53.1. High traffic ≠ most deadly.
- **Rajasthan:** 23,480 (2019) → 19,114 (2020, −18.6%) → 20,951 (+9.6%) → 23,614 (+12.7%) → **24,694 (2023, +4.6%)**. Fatalities 10,563 → 9,250 (−12.4%) → 10,043 → 11,104 → **11,762 (+5.9%)**. Severity stable **45–48 per 100**, 2023 = **47.6 (8th highest among large states)**.
- **Rajasthan rank:** accidents 7th (2019) → 9th (2020–21) → 7th (2022–23); fatalities steady **6th** (5th in 2021).

## Tableau Public dashboard (build this in ~1 hour)
Connect Tableau Public to `road_accidents_clean.csv`. Three sheets + one dashboard:
1. **Map — “2023 accidents by state”:** filled map, State → Detail/Geography, `accidents` (2023 filter) → Color, `fatalities_per_100_accidents` → Tooltip. Title: “Where crashes happen (2023)”.
2. **Trend — “Rajasthan vs India 2019–2023”:** line chart, `year` → Columns, `SUM(accidents)` → Rows, `state = Rajasthan` vs all-states average (dual axis or filter to Rajasthan + All-India computed). Add YoY labels. Shows COVID dip + rebound past 2019.
3. **Ranking — “2023 severity: deaths per 100 crashes”:** horizontal bar, top 12 by `fatalities_per_100_accidents`, Rajasthan highlighted (use color mark). Proves volume ≠ severity.
- Dashboard: title, 2-line insight (“Rajasthan 7th in crashes, 6th in deaths; 47.6 deaths/100 crashes in 2023”), source footer “Source: MoRTH via OpenCity (public domain), 2019–2023”, year filter (2019–2023).
- Publish to Tableau Public, paste the link in this README and on your resume.

Tableau tips: set `year` to discrete, `fatalities_per_100_accidents` to 1 decimal, state names match Tableau geocoding except rename “Dadra & Nagar Haveli and Daman & Diu” → Tableau recognises “Dadra and Nagar Haveli”; if geocoding fails, use state names as-is on a bar instead of forcing the map.

## Repo structure
```
data/accidents.csv        raw (OpenCity)
data/fatalities.csv       raw (OpenCity)
etl.py                    extract → transform → load
queries.sql               8 portfolio SQL queries (RANK, LAG, AVG windows)
road_accidents.db         SQLite output (generated)
road_accidents_clean.csv  Tableau input (generated)
requirements.txt
README.md
```

## Reproducibility
Python 3.10+, `pip install -r requirements.txt`, `python etl.py`. SQLite 3.x. Tableau Public (free, Windows/Mac).
