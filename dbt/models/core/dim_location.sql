{{ config(materialized='table') }}
select distinct
  {{ dbt_utils.generate_surrogate_key(['neighbourhood_group','neighbourhood']) }} as location_sk,
  neighbourhood_group,
  neighbourhood
from {{ ref('stg_listings') }}
where neighbourhood_group is not null and neighbourhood is not null
