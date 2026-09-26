{{
config(
materialized = 'incremental',
schema = 'analytics',
incremental_strategy = 'merge',
unique_key=['id']
)
}}

select      id
    ,sync_token
    ,doc_number
    ,txn_dt
    ,due_dt
    ,customer_id
    ,customer_name
    ,department_id
    ,bill_addr_city
    ,bill_addr_state
    ,bill_addr_postal_code
    ,ship_addr_city
    ,bill_email
    ,print_status
    ,email_status
    ,total_tax
    ,allow_online_payment
    ,delivery_type
    ,created_dt
    ,updated_dt 

from {{ ref('qb_invoices') }}
qualify row_number() over (
    partition by id
    order by updated_dt desc
) = 1