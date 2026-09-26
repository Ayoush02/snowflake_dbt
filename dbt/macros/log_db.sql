{% macro log_db() %}
    {#- Resolve the logging database dynamically.
        Primary: the log_database var (which maps to databases.RAW).
        Fallback: derive env prefix from target.database, like GenericLogger did. -#}
    {%- set configured = var('log_database', '') -%}
    {%- if configured and configured | trim != '' -%}
        {{ return(configured) }}
    {%- else -%}
        {%- set env_prefix = target.database.split('_')[0] -%}
        {%- if env_prefix not in ['DEV', 'PROD'] -%}
            {%- set env_prefix = 'DEV' -%}
        {%- endif -%}
        {{ return(env_prefix ~ '_RAW') }}
    {%- endif -%}
{% endmacro %}