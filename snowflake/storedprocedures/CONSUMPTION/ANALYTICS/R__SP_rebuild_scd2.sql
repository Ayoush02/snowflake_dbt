
/*
-- how to call this procedure:
-- -- 1. upload the file to a stage (from SnowSQL / Snowflake CLI)
-- PUT file:///path/to/rebuild_scd2.py @MY_DB.MY_SCHEMA.MY_STAGE
--     OVERWRITE = TRUE AUTO_COMPRESS = FALSE;

-- -- 2. (re)create the procedure pointing at it
-- --    run create_procedure.sql

-- -- 3. call it ad-hoc
-- CALL SP_REBUILD_SCD2(
--     'DEV_TRANSFORM.POSTGRES.CUSTOMERS',
--     'CONSUMPTION.ANALYTICS.DIM_CUSTOMER',
--     'customer_id',
--     'updated_dt',
--     ARRAY_CONSTRUCT(
--         'sync_token','display_name','company_name','fully_qualified_name',
--         'print_on_check_name','active','taxable','job','bill_with_parent',
--         'is_project','balance','balance_with_jobs','bill_addr_line1',
--         'bill_addr_city','bill_addr_state','bill_addr_postal_code',
--         'bill_addr_country','ship_addr_line1','ship_addr_city','ship_addr_state',
--         'ship_addr_postal_code','ship_addr_country','primary_phone',
--         'primary_email','preferred_delivery_method','sales_term_id',
--         'sales_term_name','currency_code','default_tax_code_id','notes'
--     ),
--     'created_dt'
-- );
 */
CREATE OR REPLACE PROCEDURE SP_REBUILD_SCD2(
    SOURCE_TABLE      STRING,
    TARGET_TABLE      STRING,
    KEY_COL           STRING,
    UPDATED_AT_COL    STRING,
    TRACKED_COLS      ARRAY,
    CREATED_AT_COL    STRING DEFAULT NULL,
    END_DATE          STRING DEFAULT '9999-12-31'
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
IMPORTS = ('@{{ git_repository }}/branches/{{ git_branch }}/snowflake/snowpark/CONSUMPTION/ANALYTICS/SP_REBUILD_SCD2/src/main.py')
HANDLER = 'main.run'
EXECUTE AS CALLER;
