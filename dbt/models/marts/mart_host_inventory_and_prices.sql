{{ config(materialized='view') }}
select
  dh.host_id,
  dh.host_name,
  dh.listings_count,
  avg(f.price)::numeric(10,2) as avg_price,
  percentile_cont(0.5) within group (order by f.price) as p50_price,
  stddev_pop(f.price)::numeric(10,2) as std_price
from {{ ref('fact_listing_snapshot') }} f
join {{ ref('dim_host') }} dh on dh.host_sk = f.host_sk
group by dh.host_id, dh.host_name, dh.listings_count
order by dh.listings_count desc
limit 100
