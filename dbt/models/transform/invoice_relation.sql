{{
config(
materialized = 'incremental',
incremental_strategy = 'append',
transient = false
)
}}
select ID
        ,INVOICE_ID
        ,EXTERNAL_ID
        ,CREATED_AT CREATED_DT
        ,UPDATED_AT UPDATED_DT
        ,DELETED_AT DELETED_DT
        ,DATE(TRANSFORM_TS) LOAD_DT


from {{ source('postgres','invoice_relation') }} C
{% if is_incremental() %}
where date(c.TRANSFORM_TS) > (select coalesce(max(t.load_dt),date('2010-01-01')) from {{ this }} t) 
{% endif %}