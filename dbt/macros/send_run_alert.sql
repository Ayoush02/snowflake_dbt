{% macro send_run_alert() %}
    {#- flags.WHICH gates alerting to real data runs only. on-run-end also fires
        on compile/parse (what `snow dbt deploy` does), so without this guard every
        deployment would send an email and any alert error would fail the deploy. -#}
    {% if execute and results and flags.WHICH in ('run', 'build', 'snapshot', 'seed') %}
        {%- set alert_schema = var('log_schema', 'UTILS') -%}
        {%- set log_table = log_db() ~ '.' ~ alert_schema ~ '.' ~ var('log_table', 'LOG_HISTORY') -%}

        {#- Scoped to THIS run only. log_history_from_results writes JOB_ID as
            '<invocation_id>::<node_unique_id>', so the prefix isolates this
            invocation. Scoping by CURRENT_DATE() instead would re-alert models
            that failed earlier today and were not rebuilt since. -#}
        {% set failed_sql %}
            SELECT JOB_ID
            FROM {{ log_table }}
            WHERE JOB_ID LIKE '{{ invocation_id }}::%'
              AND STATUS = 'FAILED'
        {% endset %}
        {% set failed = run_query(failed_sql) %}

        {#- Exactly one email per run either way. Both procedures take the bare
            invocation_id and roll up every row belonging to this run. -#}
        {% if failed and failed.rows | length > 0 %}
            {% set c %}
                call {{ log_db() }}.{{ alert_schema }}.SEND_FAILURE_ALERT('{{ invocation_id }}')
            {% endset %}
            {% do run_query(c) %}
        {% else %}
            {% set c %}
                call {{ log_db() }}.{{ alert_schema }}.SEND_SUCCESS_ALERT('{{ invocation_id }}')
            {% endset %}
            {% do run_query(c) %}
        {% endif %}
    {% endif %}
{% endmacro %}