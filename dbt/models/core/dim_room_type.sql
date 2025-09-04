{{ config(materialized='table') }}
select
  {{ dbt_utils.generate_surrogate_key(['room_type']) }} as room_type_sk,
  room_type
from (select distinct room_type from {{ ref('stg_listings') }}) t
where room_type is not null
