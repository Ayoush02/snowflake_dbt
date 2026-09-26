{% set deal_tracked_cols = [
    'is_archived',
    'url',
    'dealname',
    'dealstage',
    'notes_last_updated_dt',
    'notes_last_contacted_dt',
    'dealtype',
    'dealsource',
    'description',
    'num_associated_contacts',
    'closed_dt',
    'deal_location',
    'pipeline',

] %}
-- prehook parameters scd2_close_old(source_ref_name, key_column, updated_at_column, tracked_columns)
{{
    config(
        materialized='incremental',
        unique_key=['deal_id', 'start_dt'],
        incremental_strategy='append',
        schema = 'analytics',
        pre_hook=[
            "{{ scd2_close_old('deals', 'deal_id', 'updated_dt', " ~ deal_tracked_cols ~ ") }}" 
        ]
    )
}}

{{ scd2_load(
    source_relation=ref('deals'),
    key_column='deal_id',
    updated_at_column='updated_dt',
    tracked_columns=deal_tracked_cols,
    passthrough_columns=['created_dt', 'updated_dt', 'quote_id', 'load_dt']
) }}