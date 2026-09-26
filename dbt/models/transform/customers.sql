{{
config(
materialized = 'incremental',
incremental_strategy = 'merge',
transient = false
)
}}
select  id customer_id
        ,sync_token
        ,display_name
        ,coalesce(company_name,fully_qualified_name,'')company_name
        ,fully_qualified_name
        ,print_on_check_name
        ,active
        ,taxable
        ,job
        ,bill_with_parent
        ,is_project
        ,balance
        ,balance_with_jobs
        ,coalesce(bill_addr_line1,'')bill_addr_line1
        ,coalesce(bill_addr_city,'')bill_addr_city
        ,coalesce(bill_addr_state,'')bill_addr_state
        ,coalesce(bill_addr_postal_code,'')bill_addr_postal_code
        ,coalesce(bill_addr_country,'')bill_addr_country
        ,coalesce(ship_addr_line1,'')ship_addr_line1
        ,coalesce(ship_addr_city,'')ship_addr_city
        ,coalesce(ship_addr_state,'')ship_addr_state
        ,coalesce(ship_addr_postal_code,'')ship_addr_postal_code
        ,coalesce(ship_addr_country,'')ship_addr_country
        ,coalesce(primary_phone,'')primary_phone
        ,coalesce(primary_email,'')primary_email
        ,preferred_delivery_method
        ,coalesce(sales_term_id,0)sales_term_id
        ,coalesce(sales_term_name,'')sales_term_name
        ,currency_code
        ,default_tax_code_id
        ,coalesce(notes,'')notes
        ,date(created_at) created_dt
        ,date(updated_at) updated_dt
        ,date(load_time) load_dt
from {{ source('postgres','customers') }} c
{% if is_incremental() %}
where date(c.load_time) > (select coalesce(max(t.load_dt),date('2010-01-01')) from {{ this }} t) 
{% endif %}