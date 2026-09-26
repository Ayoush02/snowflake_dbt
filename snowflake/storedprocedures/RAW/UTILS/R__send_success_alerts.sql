CREATE OR REPLACE PROCEDURE SEND_SUCCESS_ALERT("JOB_ID" VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    v_model_count    NUMBER;
    v_rows_processed NUMBER;
    v_duration       FLOAT;
    v_run_start      TIMESTAMP_LTZ;
    v_detail_rows    VARCHAR;
    v_email_subject  VARCHAR;
    v_email_body     VARCHAR;
BEGIN
    -- The dbt macro log_history_from_results writes JOB_ID as
    -- '<invocation_id>::<node_unique_id>', so ONE dbt run logs one row per
    -- model. This procedure is called with the bare invocation_id, which
    -- matches no single row - hence the prefix match and the rollup below.
    SELECT COUNT(*),
           COALESCE(SUM(ROWS_PROCESSED), 0),
           COALESCE(SUM(DURATION_SECONDS), 0),
           MIN(START_TIME)
      INTO :v_model_count, :v_rows_processed, :v_duration, :v_run_start
      FROM {{ databases.RAW }}.UTILS.LOG_HISTORY
     WHERE JOB_ID LIKE :JOB_ID || '::%';

    -- No rows for this run: return instead of emailing. Passing a NULL subject
    -- or body to SYSTEM$SEND_EMAIL raises STATEMENT_ERROR, which would fail the
    -- entire dbt run because this is called from an on-run-end hook.
    IF (:v_model_count = 0) THEN
        RETURN 'No log rows found for this run - success alert skipped.';
    END IF;

    -- One <tr> per model. Every column is COALESCEd because in SQL a single
    -- NULL anywhere in a concatenation makes the ENTIRE string NULL.
    SELECT LISTAGG(
               '<tr>' ||
               '<td>' || COALESCE(SP_NAME, '?') || '</td>' ||
               '<td>' || COALESCE(SP_DATABASE, '') || '.' || COALESCE(SP_SCHEMA, '') || '</td>' ||
               '<td>' || COALESCE(STATUS, '') || '</td>' ||
               '<td align="right">' || COALESCE(ROWS_PROCESSED, 0) || '</td>' ||
               '<td align="right">' || ROUND(COALESCE(DURATION_SECONDS, 0), 2) || '</td>' ||
               '</tr>', ''
           ) WITHIN GROUP (ORDER BY START_TIME)
      INTO :v_detail_rows
      FROM {{ databases.RAW }}.UTILS.LOG_HISTORY
     WHERE JOB_ID LIKE :JOB_ID || '::%';

    v_email_subject := '✅ MDC Alert: dbt run SUCCESS (' || :v_model_count || ' models)';

    v_email_body := '
    <div style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; max-width: 700px; margin: auto;">
        <div style="background-color: #28a745; padding: 15px; color: white; text-align: center;">
            <h2 style="margin: 0;">dbt Run Successful</h2>
        </div>
        <div style="padding: 20px; color: #333;">
            <p><strong>Run ID:</strong> ' || COALESCE(:JOB_ID, 'n/a') || '</p>
            <p><strong>Started:</strong> ' || COALESCE(TO_VARCHAR(:v_run_start), 'n/a') || '</p>
            <p><strong>Models:</strong> ' || :v_model_count || '</p>
            <p><strong>Total Rows Processed:</strong> ' || :v_rows_processed || '</p>
            <p><strong>Total Duration:</strong> ' || ROUND(:v_duration, 2) || ' seconds</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
            <p><strong>Model Detail:</strong></p>
            <table cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 12px;">
                <tr style="background: #f1f3f5; text-align: left;">
                    <th>Model</th><th>Target</th><th>Status</th><th align="right">Rows</th><th align="right">Seconds</th>
                </tr>' || COALESCE(:v_detail_rows, '') || '
            </table>
        </div>
    </div>';

    CALL SYSTEM$SEND_EMAIL(
        'EMAIL_NOTIFY_INTEGRATION',
        'abhij.it.bangal92@gmail.com',
        :v_email_subject,
        :v_email_body,
        'text/html'
    );

    RETURN 'Success alert sent for ' || :v_model_count || ' model(s).';
END;
$$;
