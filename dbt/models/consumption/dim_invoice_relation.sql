{{
config(
materialized = 'incremental',
schema = 'analytics',
incremental_strategy = 'merge',
unique_key='INVOICE_ID'
)
}}

select  * 
from {{ ref('invoice_relation') }}
qualify row_number() over (
    partition by INVOICE_ID
    order by updated_dt desc
) = 1