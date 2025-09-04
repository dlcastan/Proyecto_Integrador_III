with src as (
  select * from {{ source('raw','ab_nyc') }}
)
select
  id,
  cast(host_id as bigint) as host_id,
  nullif(trim(host_name),'') as host_name,
  nullif(neighbourhood_group,'') as neighbourhood_group,
  nullif(neighbourhood,'') as neighbourhood,
  cast(latitude as double precision) as latitude,
  cast(longitude as double precision) as longitude,
  nullif(room_type,'') as room_type,
  cast(price as int) as price,
  greatest(cast(minimum_nights as int),1) as minimum_nights,
  cast(number_of_reviews as int) as number_of_reviews,
  last_review as last_review,                             -- <-- cambio
  cast(reviews_per_month as numeric(10,2)) as reviews_per_month,
  cast(calculated_host_listings_count as int) as host_listings_count,
  least(greatest(cast(availability_365 as int),0),365) as availability_365,
  current_date as snapshot_date
from src
