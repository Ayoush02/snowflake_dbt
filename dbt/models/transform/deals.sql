{{
config(
materialized = 'incremental',
incremental_strategy = 'append',
transient = false
)
}}
select 
    deal_id
    ,is_archived
    ,created_at created_dt
    ,updated_at updated_dt
    ,url
    ,dealname
    ,dealstage 
    ,date(notes_last_updated)notes_last_updated_dt
    ,date(notes_last_contacted)notes_last_contacted_dt
    ,dealtype
    ,coalesce(deal_source,'')dealsource
    ,amount
    ,coalesce(description,'')description
    ,num_associated_contacts
    ,date(closedate)closed_Dt
    ,deal_location
    ,mdc_quote_id quote_id
    ,pipeline
    ,hs_acv acv 
    ,hs_Arr arr
    ,date(load_time)load_dt
from {{ source('postgres','deals') }} c
{% if is_incremental() %}
where date(c.load_time) > (select coalesce(max(t.load_dt),date('2010-01-01')) from {{ this }} t) 
{% endif %}