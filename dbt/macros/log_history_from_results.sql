{% macro log_history_from_results(results) %}
    {#- Runs at on-run-end. Writes one LOG_HISTORY row per node, including failures. -#}
    {#- flags.WHICH gates this to real data runs only. on-run-end also fires on
        compile/parse, which is what `snow dbt deploy` does when publishing the
        project - logging there would record SUCCESS rows for models that were
        never materialized, and a failure here would break the deployment. -#}
    {% if execute and results and flags.WHICH in ('run', 'build', 'snapshot', 'seed') %}

        {%- set target_table = log_db() ~ '.' ~ var('log_schema', 'UTILS') ~ '.' ~ var('log_table', 'LOG_HISTORY') -%}

        {% set rows = [] %}
        {% for res in results %}

            {%- set job_id      = invocation_id ~ '::' ~ res.node.unique_id -%}
            {%- set sp_name     = res.node.name -%}
            {%- set sp_database = res.node.database -%}
            {%- set sp_schema   = res.node.schema -%}
            {%- set duration    = res.execution_time if res.execution_time is not none else 0 -%}
            {%- set message     = (res.message or '') | replace("$$", "") -%}

            {#- map dbt statuses to your logger's vocabulary -#}
            {%- if res.status in ['error', 'fail'] -%}
                {%- set status = 'FAILED' -%}
            {%- elif res.status in ['success', 'pass'] -%}
                {%- set status = 'SUCCESS' -%}
            {%- elif res.status == 'skipped' -%}
                {%- set status = 'SKIPPED' -%}
            {%- else -%}
                {%- set status = res.status | upper -%}
            {%- endif -%}

            {#- best-effort row count -#}
            {%- set rows_done = 0 -%}
            {%- if res.adapter_response and res.adapter_response.get('rows_affected') is not none -%}
                {%- set rows_done = res.adapter_response.get('rows_affected') -%}
            {%- endif -%}

            {#- INPUT_PARAMS is NULL rather than an empty JSON object: Snowflake
                rejects VARIANT-producing functions like TRY_PARSE_JSON() inside an
                INSERT ... VALUES clause ("Invalid expression in VALUES clause").
                Populating it would need INSERT ... SELECT instead. -#}
            {%- set row -%}
                (
                    '{{ job_id }}',
                    '{{ sp_name }}',
                    '{{ sp_database }}',
                    '{{ sp_schema }}',
                    NULL,
                    'INFO',
                    dateadd('second', -1 * {{ duration }}, current_timestamp()),
                    '{{ status }}',
                    current_user(),
                    current_timestamp(),
                    {{ duration }},
                    {{ rows_done }},
                    $${{ message }}$$
                )
            {%- endset -%}
            {% do rows.append(row) %}

        {% endfor %}

        {% if rows | length > 0 %}
            {% set insert_sql %}
                insert into {{ target_table }}
                    (JOB_ID, SP_NAME, SP_DATABASE, SP_SCHEMA, INPUT_PARAMS,
                     LOG_LEVEL, START_TIME, STATUS, EXECUTED_BY,
                     END_TIME, DURATION_SECONDS, ROWS_PROCESSED, MESSAGE)
                values
                {{ rows | join(",\n") }}
            {% endset %}
            {% do run_query(insert_sql) %}
        {% endif %}

    {% endif %}
{% endmacro %}