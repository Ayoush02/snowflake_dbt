{{
config(
materialized = 'incremental',
incremental_strategy = 'append',
transient = false
)
}}
select 
        quote_id
        ,is_archived
        ,created_at created_dt
        ,updated_at updated_dt
        ,url
        ,hs_status status
        ,hs_payment_status payment_status
        ,date(hs_payment_date) payment_dt
        ,date(hs_expiration_date) expiration_dt
        ,coalesce(hs_render_status,'')render_status
        ,hs_tcv tcv
        ,hs_title title
        ,hs_quote_amount quote_amount
        ,date(load_time) load_dt        

from {{ source('postgres','parsed_quotes') }} c
{% if is_incremental() %}
where date(c.load_time) > (select coalesce(max(t.load_dt),date('2010-01-01')) from {{ this }} t) 
{% endif %}