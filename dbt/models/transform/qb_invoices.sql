{{
config(
materialized = 'incremental',
incremental_strategy = 'append',
transient = false
)
}}
select 
    id
    ,sync_token
    ,doc_number
    ,txn_date txn_dt
    ,due_date due_dt
    ,total_amt total_amount
    ,balance 
    ,customer_id
    ,customer_name
    ,department_id
    ,coalesce(bill_addr_city,'')bill_addr_city
    ,coalescE(bill_addr_state,'')bill_addr_state
    ,coalesce(bill_addr_postal_code,'')bill_addr_postal_code
    ,coalesce(ship_addr_city,'')ship_addr_city
    ,coalesce(bill_email,'')bill_email
    ,print_status
    ,email_status
    ,total_tax
    ,allow_online_payment
    ,coalesce(delivery_type,'')delivery_type
    ,date(created_At)created_dt
    ,date(updated_at)updated_dt
    ,date(load_time)load_dt

from {{ source('postgres','qb_invoices') }} c
{% if is_incremental() %}
where date(c.load_time) > (select coalesce(max(t.load_dt),date('2010-01-01')) from {{ this }} t) 
{% endif %}