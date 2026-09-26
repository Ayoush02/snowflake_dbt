{% macro scd2_load(source_relation, key_column, updated_at_column, tracked_columns, passthrough_columns=[], end_date='9999-12-31') %}

    
    {%- set unchanged_predicate -%}
        {%- for col in tracked_columns -%}
            s.{{ col }} is not distinct from t.{{ col }}{{ " and " if not loop.last }}
        {%- endfor -%}
    {%- endset -%}

    {%- set all_cols = [key_column] + tracked_columns + passthrough_columns -%}

    {%- if not is_incremental() -%}

        {#- ---------- FIRST RUN: seed every row as version 1 ---------- -#}
        select
            {%- for col in all_cols %}
            {{ col }},
            {%- endfor %}
            {{ updated_at_column }} as start_dt,
            date('{{ end_date }}') as end_dt,
            true as is_active
        from {{ source_relation }} s
        qualify row_number() over (
            partition by {{ key_column }} order by {{ updated_at_column }} desc
        ) = 1

    {%- else -%}

        {#- ---------- INCREMENTAL RUN: only new/changed source rows ---------- -#}
        {#- The close-out of old versions happens in a pre-hook (see model). -#}
        select
            {%- for col in all_cols %}
            s.{{ col }},
            {%- endfor %}
            s.{{ updated_at_column }} as start_dt,
            date('{{ end_date }}') as end_dt,
            true as is_active
        from {{ source_relation }} s
        where not exists (
            select 1 from {{ this }} t
            where s.{{ key_column }} = t.{{ key_column }}
              and {{ unchanged_predicate }}
        )
        qualify row_number() over (
            partition by s.{{ key_column }} order by s.{{ updated_at_column }} desc
        ) = 1

    {%- endif -%}

{% endmacro %}