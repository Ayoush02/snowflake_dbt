{{
config(
materialized = 'incremental',
schema = 'analytics',
incremental_strategy = 'merge',
unique_key=['quote_id','deal_id'],
)
}}
select  distinct * 
        
from {{ ref('assoc_quotes_deals') }}
