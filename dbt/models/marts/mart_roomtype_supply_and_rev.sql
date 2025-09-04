{{ config(materialized='view') }}
with base as (
  select room_type_sk, count(*) as listings,
         sum( greatest(365 - availability_365, 0) * price )::numeric(18,2) as revenue_est
  from {{ ref('fact_listing_snapshot') }}
  group by room_type_sk
)
select
  dr.room_type,
  b.listings,
  b.revenue_est
from base b
join {{ ref('dim_room_type') }} dr on dr.room_type_sk = b.room_type_sk
order by listings desc
