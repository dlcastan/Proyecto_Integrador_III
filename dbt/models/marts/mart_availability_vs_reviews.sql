{{ config(materialized='view') }}
select
  dl.neighbourhood_group,
  corr( (365 - f.availability_365)::numeric, coalesce(f.reviews_per_month,0)::numeric ) as corr_occ_reviews
from {{ ref('fact_listing_snapshot') }} f
join {{ ref('dim_location') }} dl on dl.location_sk = f.location_sk
group by 1
order by 1
