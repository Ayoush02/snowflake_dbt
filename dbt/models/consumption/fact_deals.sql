{{
config(
materialized = 'incremental',
schema = 'analytics',
incremental_strategy = 'merge',
unique_key=['deal_id','quote_id'],
merge_update_columns=['amount','acv','arr','updated_dt','closed_Dt']
)
}}

select      deal_id
            ,quote_id
            ,amount
            ,acv 
            ,arr
            ,created_dt
            ,updated_dt
            ,closed_Dt
            ,load_dt
from {{ ref('deals') }}
qualify row_number() over (
    partition by deal_id, quote_id
    order by updated_dt desc
) = 1