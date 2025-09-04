{{ config(materialized='view') }}
select
  dl.neighbourhood_group,
  dl.neighbourhood,
  avg(f.price)::numeric(10,2) as avg_price
from {{ ref('fact_listing_snapshot') }} f
join {{ ref('dim_location') }} dl on dl.location_sk = f.location_sk
group by 1,2
