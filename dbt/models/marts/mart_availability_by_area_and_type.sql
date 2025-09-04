{{ config(materialized='view') }}
select
  dl.neighbourhood_group,
  dl.neighbourhood,
  dr.room_type,
  avg(f.availability_365)::numeric(10,2) as avg_availability
from {{ ref('fact_listing_snapshot') }} f
join {{ ref('dim_location') }} dl on dl.location_sk = f.location_sk
join {{ ref('dim_room_type') }} dr on dr.room_type_sk = f.room_type_sk
group by 1,2,3
