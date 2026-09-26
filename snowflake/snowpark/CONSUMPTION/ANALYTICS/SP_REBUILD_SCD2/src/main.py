def run(session, source_table, target_table, key_col, updated_at_col,
        tracked_cols, created_at_col, end_date):

    if not tracked_cols:
        return "ERROR: TRACKED_COLS must contain at least one column."

    stg = target_table + "_STG"

    # per-column fragments
    lag_lines = ",\n        ".join(
        f"{c},\n        LAG({c}) OVER (PARTITION BY {key_col} "
        f"ORDER BY {updated_at_col}) AS prev_{c}"
        for c in tracked_cols
    )

    distinct_checks = "\n            OR ".join(
        f"{c} IS DISTINCT FROM prev_{c}" for c in tracked_cols
    )

    final_cols = [key_col] + list(tracked_cols)
    if created_at_col:
        final_cols.append(created_at_col)
    final_col_list = ",\n        ".join(final_cols)

    created_frag = f",\n        {created_at_col}" if created_at_col else ""

    full_query = f"""
    WITH change AS (
        SELECT
            {key_col},
            {updated_at_col},
            {lag_lines}{created_frag}
        FROM {source_table}
    ),
    change_indi AS (
        SELECT *,
            CASE WHEN {distinct_checks} THEN 1 ELSE 0 END AS is_changed
        FROM change
    ),
    changed_only AS (
        SELECT *,
            SUM(is_changed) OVER (PARTITION BY {key_col}
                ORDER BY {updated_at_col}) AS streak
        FROM change_indi
        WHERE is_changed <> 0
    )
    SELECT
        {final_col_list},
        {updated_at_col},
        {updated_at_col} AS start_dt,
        COALESCE(LEAD({updated_at_col}, 1) OVER (
            PARTITION BY {key_col} ORDER BY {updated_at_col}),
            DATE('{end_date}')) AS end_dt,
        CASE WHEN LEAD({updated_at_col}, 1) OVER (
            PARTITION BY {key_col} ORDER BY {updated_at_col})
            IS NULL THEN TRUE ELSE FALSE END AS is_active
    FROM changed_only
    """

    try:
        # build into staging, then swap so target is never empty
        session.sql(f"CREATE OR REPLACE TABLE {stg} AS {full_query}").collect()
        session.sql(f"ALTER TABLE {target_table} SWAP WITH {stg}").collect()
        session.sql(f"DROP TABLE IF EXISTS {stg}").collect()
        return f"SUCCESS: rebuilt {target_table} from {source_table}"
    except Exception as err:
        return f"ERROR: {str(err)}"