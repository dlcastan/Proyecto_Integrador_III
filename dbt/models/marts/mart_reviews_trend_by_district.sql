{{ config(materialized='view') }}
select
  dd.year, dd.month,
  dl.neighbourhood_group,
  sum(coalesce(f.reviews_per_month,0))::numeric(10,2) as reviews_pm
from {{ ref('fact_listing_snapshot') }} f
join {{ ref('dim_date') }} dd on dd.date_sk = f.date_sk
join {{ ref('dim_location') }} dl on dl.location_sk = f.location_sk
group by 1,2,3
order by 1,2,3
