{{
config(
materialized = 'table',
transient = true
)
}}
select * from {{ source('postgres','assoc_quotes_deals') }}