{{ config(materialized='table') }}
with dates as (
  select generate_series(
           date '2015-01-01',
           date '2035-12-31',
           interval '1 day')::date as d
)
select
  cast(to_char(d,'YYYYMMDD') as int) as date_sk,
  d as full_date,
  extract(year from d)::smallint as year,
  extract(quarter from d)::smallint as quarter,
  extract(month from d)::smallint as month,
  extract(day from d)::smallint as day,
  extract(isodow from d)::smallint as day_of_week,
  extract(week from d)::smallint as week_of_year,
  (extract(isodow from d) in (6,7)) as is_weekend
from dates
