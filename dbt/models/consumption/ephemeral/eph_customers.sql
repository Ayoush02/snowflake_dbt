with customers as
(
select
         customer_id
        ,sync_token
        ,display_name
        ,company_name
        ,fully_qualified_name
        ,print_on_check_name
        ,active
        ,taxable
        ,job
        ,bill_with_parent
        ,is_project
        ,balance
        ,balance_with_jobs
        ,bill_addr_line1
        ,bill_addr_city
        ,bill_addr_state
        ,bill_addr_postal_code
        ,bill_addr_country
        ,ship_addr_line1
        ,ship_addr_city
        ,ship_addr_state
        ,ship_addr_postal_code
        ,ship_addr_country
        ,primary_phone
        ,primary_email
        ,preferred_delivery_method
        ,sales_term_id
        ,sales_term_name
        ,currency_code
        ,default_tax_code_id
        ,notes
        ,created_dt
        ,updated_dt
        ,load_dt

    from {{ ref('customers') }}
)
select * from customers
qualify (row_number() over(partition by customer_id order by updated_dt desc)) = 1