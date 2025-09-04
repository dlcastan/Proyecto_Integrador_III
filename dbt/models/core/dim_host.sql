{{ config(materialized='table') }}

with src as (
  select
    cast(nullif(trim(host_id::text), '') as bigint) as host_id,
    host_name,
    host_listings_count as host_listings_count
  from {{ ref('stg_listings') }}
  where host_id is not null
),

agg as (
  select
    {{ dbt_utils.generate_surrogate_key(['host_id']) }} as host_sk,
    host_id,
    max(host_name) as host_name,
    max(coalesce(host_listings_count,0))::int as listings_count,
    (max(coalesce(host_listings_count,0)) >= 5) as is_multilister,
    current_timestamp as updated_at
  from src
  group by host_id
)

select * from agg
