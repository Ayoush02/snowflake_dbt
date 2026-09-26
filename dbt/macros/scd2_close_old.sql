{% macro scd2_close_old(source_ref_name, key_column, updated_at_column, tracked_columns) %}
    {%- if is_incremental() -%}

        {%- set changed_predicate -%}
            {%- for col in tracked_columns -%}
                s.{{ col }} is distinct from t.{{ col }}{{ " or " if not loop.last }}
            {%- endfor -%}
        {%- endset -%}

        update {{ this }} t
        set is_active = false,
            end_dt = s.{{ updated_at_column }}
        from (
            select * from {{ ref(source_ref_name) }}
            qualify row_number() over (
                partition by {{ key_column }}
                order by {{ updated_at_column }} desc) = 1
        ) s
        where s.{{ key_column }} = t.{{ key_column }}
          and t.is_active = true
          and ({{ changed_predicate }})

    {%- else -%}
        select 1  {#- no-op on first run: no history to close -#}
    {%- endif -%}
{% endmacro %}