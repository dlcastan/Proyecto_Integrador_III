{{ config(materialized='table') }}

with base as (
  select
    id as listing_id,
    cast(to_char(snapshot_date,'YYYYMMDD') as int) as date_sk,
    host_id,
    neighbourhood_group, neighbourhood,
    room_type,
    price, minimum_nights, number_of_reviews, reviews_per_month, availability_365
  from {{ ref('stg_listings') }}
),
joined as (
  select
    b.listing_id, b.date_sk,
    dh.host_sk,
    dl.location_sk,
    drt.room_type_sk,
    b.price, b.minimum_nights, b.number_of_reviews, b.reviews_per_month, b.availability_365,
    (b.price = 0) as is_price_zero,
    (b.reviews_per_month is null) as has_no_reviews
  from base b
  left join {{ ref('dim_host') }}      dh  on dh.host_id = b.host_id
  left join {{ ref('dim_location') }}  dl  on dl.neighbourhood_group = b.neighbourhood_group and dl.neighbourhood = b.neighbourhood
  left join {{ ref('dim_room_type') }} drt on drt.room_type = b.room_type
)
select * from joined
