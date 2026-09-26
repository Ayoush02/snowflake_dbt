CREATE OR REPLACE PROCEDURE SEND_FAILURE_ALERT("JOB_ID" VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    v_total_count   NUMBER;
    v_failed_count  NUMBER;
    v_run_start     TIMESTAMP_LTZ;
    v_detail_blocks VARCHAR;
    v_email_subject VARCHAR;
    v_email_body    VARCHAR;
BEGIN
    -- Called once per dbt run with the bare invocation_id. The dbt macro
    -- log_history_from_results writes JOB_ID as '<invocation_id>::<node_unique_id>',
    -- so the prefix match gathers every model belonging to this one run.
    SELECT COUNT(*),
           COUNT_IF(STATUS = 'FAILED'),
           MIN(START_TIME)
      INTO :v_total_count, :v_failed_count, :v_run_start
      FROM {{ databases.RAW }}.UTILS.LOG_HISTORY
     WHERE JOB_ID LIKE :JOB_ID || '::%';

    -- Nothing failed (or nothing logged): return instead of emailing. A NULL
    -- subject/body makes SYSTEM$SEND_EMAIL raise STATEMENT_ERROR, which would
    -- fail the whole dbt run because this is called from an on-run-end hook.
    IF (:v_failed_count = 0) THEN
        RETURN 'No failed rows for this run - failure alert skipped.';
    END IF;

    -- One block per FAILED model only, each with its error text.
    -- The message is HTML-escaped (& before < and > so the escapes are not
    -- double-escaped) because dbt error text often contains angle brackets,
    -- and truncated so a few long stack traces cannot blow the email size limit.
    SELECT LISTAGG(
               '<div style="border-left: 3px solid #dc3545; padding: 8px 12px; margin-bottom: 12px; background: #fff5f5;">' ||
               '<p style="margin: 0 0 6px 0;"><strong>' || COALESCE(SP_NAME, '?') || '</strong>' ||
               ' &middot; ' || COALESCE(SP_DATABASE, '') || '.' || COALESCE(SP_SCHEMA, '') ||
               ' &middot; ' || ROUND(COALESCE(DURATION_SECONDS, 0), 2) || 's</p>' ||
               '<p style="margin: 0; font-family: monospace; font-size: 12px; color: #dc3545; white-space: pre-wrap;">' ||
               LEFT(
                   REPLACE(
                       REPLACE(
                           REPLACE(COALESCE(MESSAGE, 'No error message recorded.'), '&', '&amp;'),
                           '<', '&lt;'),
                       '>', '&gt;'),
                   1500
               ) ||
               '</p></div>', ''
           ) WITHIN GROUP (ORDER BY START_TIME)
      INTO :v_detail_blocks
      FROM {{ databases.RAW }}.UTILS.LOG_HISTORY
     WHERE JOB_ID LIKE :JOB_ID || '::%'
       AND STATUS = 'FAILED';

    v_email_subject := '❌ MDC Alert: dbt run FAILED ('
                       || :v_failed_count || ' of ' || :v_total_count || ' models)';

    v_email_body := '
    <div style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; max-width: 700px; margin: auto;">
        <div style="background-color: #dc3545; padding: 15px; color: white; text-align: center;">
            <h2 style="margin: 0;">dbt Run Failed</h2>
        </div>
        <div style="padding: 20px; color: #333;">
            <p><strong>Run ID:</strong> ' || COALESCE(:JOB_ID, 'n/a') || '</p>
            <p><strong>Started:</strong> ' || COALESCE(TO_VARCHAR(:v_run_start), 'n/a') || '</p>
            <p><strong>Failed:</strong> ' || :v_failed_count || ' of ' || :v_total_count || ' models</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
            <p><strong>Failed Models:</strong></p>
            ' || COALESCE(:v_detail_blocks, '') || '
        </div>
    </div>';

    CALL SYSTEM$SEND_EMAIL(
        'EMAIL_NOTIFY_INTEGRATION',
        'abhij.it.bangal92@gmail.com',
        :v_email_subject,
        :v_email_body,
        'text/html'
    );

    RETURN 'Failure alert sent for ' || :v_failed_count || ' model(s).';
END;
$$;
