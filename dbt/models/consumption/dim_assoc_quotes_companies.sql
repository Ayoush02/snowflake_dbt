{{
config(
materialized = 'incremental',
schema = 'analytics',
incremental_strategy = 'merge',
unique_key=['quote_id','company_id'],
)
}}

select  distinct * 
        
from {{ ref('assoc_quotes_companies') }}
