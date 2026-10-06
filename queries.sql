-- India Road Accidents 2019-2023 — portfolio queries
-- DB: road_accidents.db, table: road_accidents(state, year, accidents, fatalities,
--        fatalities_per_100_accidents, accidents_yoy_pct, fatalities_yoy_pct)
-- Source: OpenCity / MoRTH (public domain)

-- Q1. Top 10 states by accidents in 2023, with RANK() window function
SELECT
  state,
  accidents,
  fatalities,
  fatalities_per_100_accidents,
  RANK() OVER (ORDER BY accidents DESC) AS accident_rank_2023
FROM road_accidents
WHERE year = 2023
ORDER BY accidents DESC
LIMIT 10;

-- Q2. Top 10 states by fatalities in 2023, with RANK()
SELECT
  state,
  fatalities,
  accidents,
  fatalities_per_100_accidents,
  RANK() OVER (ORDER BY fatalities DESC) AS fatality_rank_2023
FROM road_accidents
WHERE year = 2023
ORDER BY fatalities DESC
LIMIT 10;

-- Q3. Severity ranking 2023: fatalities per 100 accidents (min 1000 accidents to avoid small-UT noise)
SELECT
  state,
  accidents,
  fatalities,
  fatalities_per_100_accidents,
  RANK() OVER (ORDER BY fatalities_per_100_accidents DESC) AS severity_rank_2023
FROM road_accidents
WHERE year = 2023 AND accidents >= 1000
ORDER BY fatalities_per_100_accidents DESC
LIMIT 10;

-- Q4. Rajasthan trend 2019-2023 with LAG() year-on-year change (recomputed in SQL)
SELECT
  year,
  accidents,
  fatalities,
  fatalities_per_100_accidents,
  LAG(accidents) OVER (ORDER BY year) AS prev_accidents,
  ROUND((accidents - LAG(accidents) OVER (ORDER BY year)) * 100.0
        / LAG(accidents) OVER (ORDER BY year), 2) AS accidents_yoy_pct_sql,
  LAG(fatalities) OVER (ORDER BY year) AS prev_fatalities,
  ROUND((fatalities - LAG(fatalities) OVER (ORDER BY year)) * 100.0
        / LAG(fatalities) OVER (ORDER BY year), 2) AS fatalities_yoy_pct_sql
FROM road_accidents
WHERE state = 'Rajasthan'
ORDER BY year;

-- Q5. Rajasthan's all-India rank each year (rank via CTE, then filter — filtering before ranking is a common mistake)
WITH ranked AS (
  SELECT
    year, state, accidents, fatalities,
    RANK() OVER (PARTITION BY year ORDER BY accidents DESC) AS acc_rank,
    RANK() OVER (PARTITION BY year ORDER BY fatalities DESC) AS fat_rank
  FROM road_accidents
)
SELECT year, state, accidents, acc_rank, fatalities, fat_rank
FROM ranked
WHERE state = 'Rajasthan'
ORDER BY year;

-- Q6. COVID dip + rebound: all-India totals per year with LAG()
SELECT
  year,
  SUM(accidents) AS total_accidents,
  SUM(fatalities) AS total_fatalities,
  ROUND(SUM(fatalities) * 100.0 / SUM(accidents), 2) AS severity_per_100,
  LAG(SUM(accidents)) OVER (ORDER BY year) AS prev_total_accidents,
  ROUND((SUM(accidents) - LAG(SUM(accidents)) OVER (ORDER BY year)) * 100.0
        / LAG(SUM(accidents)) OVER (ORDER BY year), 2) AS yoy_pct_sql
FROM road_accidents
GROUP BY year
ORDER BY year;

-- Q7. 3-year moving average of accidents per state (AVG() window) — sample for Rajasthan + top states
SELECT
  state, year, accidents,
  ROUND(AVG(accidents) OVER (
    PARTITION BY state ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  ), 1) AS accidents_3yr_moving_avg
FROM road_accidents
WHERE state IN ('Rajasthan', 'Tamil Nadu', 'Madhya Pradesh', 'Uttar Pradesh', 'Kerala', 'Karnataka')
ORDER BY state, year;

-- Q8. Biggest YoY jump in accidents, 2022 -> 2023 (uses stored ETL column; verify against LAG version)
SELECT state, year, accidents, accidents_yoy_pct
FROM road_accidents
WHERE year = 2023
ORDER BY accidents_yoy_pct DESC
LIMIT 10;
