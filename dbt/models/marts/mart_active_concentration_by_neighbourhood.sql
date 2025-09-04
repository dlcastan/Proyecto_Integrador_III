{{ config(materialized='view') }}
with active as (
  select location_sk
  from {{ ref('fact_listing_snapshot') }}
  where price > 0 and availability_365 > 0
)
select
  dl.neighbourhood_group,
  dl.neighbourhood,
  count(*) as active_listings
from active a
join {{ ref('dim_location') }} dl on dl.location_sk = a.location_sk
group by 1,2
order by active_listings desc
