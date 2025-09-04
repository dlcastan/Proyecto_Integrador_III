{{ config(materialized='view') }}
with stats as (
  select
    dl.neighbourhood_group,
    percentile_cont(0.25) within group (order by f.price) as p25,
    percentile_cont(0.50) within group (order by f.price) as p50,
    percentile_cont(0.75) within group (order by f.price) as p75
  from {{ ref('fact_listing_snapshot') }} f
  join {{ ref('dim_location') }} dl on dl.location_sk = f.location_sk
  group by 1
),
joined as (
  select
    f.price,
    dl.neighbourhood_group,
    s.p25, s.p50, s.p75,
    (s.p75 - s.p25) as iqr
  from {{ ref('fact_listing_snapshot') }} f
  join {{ ref('dim_location') }} dl on dl.location_sk = f.location_sk
  join stats s on s.neighbourhood_group = dl.neighbourhood_group
)
select
  neighbourhood_group,
  p25, p50, p75,
  count(*) filter (where price > p75 + 1.5*iqr) as outliers_hi,
  count(*) filter (where price < p25 - 1.5*iqr) as outliers_lo
from joined
group by 1,2,3,4
