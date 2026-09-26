{% set deal_tracked_cols = [
         'is_archived'
        ,'url'
        ,'status'
        ,'payment_status'
        ,'payment_dt'
        ,'expiration_dt'
        ,'render_status'
        ,'title'
        
] %}
-- prehook parameters scd2_close_old(source_ref_name, key_column, updated_at_column, tracked_columns)
{{
    config(
        materialized='incremental',
        unique_key=['quote_id', 'start_dt'],
        incremental_strategy='append',
        schema = 'analytics',
        pre_hook=[
            "{{ scd2_close_old('parsed_quotes', 'quote_id', 'updated_dt', " ~ deal_tracked_cols ~ ") }}" 
        ]
    )
}}

{{ scd2_load(
    source_relation=ref('parsed_quotes'),
    key_column='quote_id',
    updated_at_column='updated_dt',
    tracked_columns=deal_tracked_cols,
    passthrough_columns=['created_dt', 'updated_dt', 'load_dt']
) }}