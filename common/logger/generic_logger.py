import logging
import time
import uuid
import json
from snowflake.snowpark import Session
from snowflake.telemetry import add_event, set_span_attribute

class GenericLogger:
    def __init__(self, session: Session, sp_name: str, log_db: str = None):
        self.session = session
        self.job_id = str(uuid.uuid4())
        self.sp_name = sp_name
        self.start_time = time.time()
        self.rows_processed = 0
        self.logger = logging.getLogger(sp_name)
        
        if log_db:
            self.current_db = log_db
        else:
            # Fall back to new approach 
            sp_parts = sp_name.split(".")
            if len(sp_parts) >= 3 and "_" in sp_parts[0]:
                env_prefix = sp_parts[0].split("_")[0]
                if env_prefix in ("DEV", "PROD"):  # validated whitelist
                    self.current_db = f"{env_prefix}_RAW"
                else:
                    self.current_db = "DEV_RAW"  # safe fallback
            else:
                raise ValueError(
                    f"sp_name '{sp_name}' must be fully qualified "
                    f"(DATABASE.SCHEMA.PROCNAME) when log_db is not provided."
                )

    def log_start(self, input_params: dict = None, log_level: str = "INFO"):
        sp_parts = self.sp_name.split(".")
        sp_database = sp_parts[0] if len(sp_parts) >= 1 else ""
        sp_schema = sp_parts[1] if len(sp_parts) >= 2 else ""
        sp_proc = sp_parts[-1]
        params_json = json.dumps(input_params) if input_params else "{}"

        # Use f-string for the database name, keep parameterized (?) for the values
        query = f"""
            INSERT INTO {self.current_db}.UTILS.LOG_HISTORY
            (JOB_ID, SP_NAME, SP_DATABASE, SP_SCHEMA,
             INPUT_PARAMS, LOG_LEVEL, START_TIME, STATUS, EXECUTED_BY)
            SELECT ?, ?, ?, ?, TRY_PARSE_JSON(?), ?, CURRENT_TIMESTAMP(), 'RUNNING', CURRENT_USER()
        """
        params = [self.job_id, sp_proc, sp_database, sp_schema, params_json, log_level]
        
        try:
            self.session.sql(query, params=params).collect()
        except Exception as e:
            # Fail silently so logging issues don't crash the pipeline
            self.logger.warning(f"[JOB_ID:{self.job_id}] Failed to insert log_start record: {e}")

        msg = f"[JOB_ID:{self.job_id}] [START] {self.sp_name} started"
        self.logger.info(msg)
        add_event("procedure_started", {"job_id": self.job_id, "sp_name": self.sp_name})
        set_span_attribute("job_id", self.job_id)
        
        return self.job_id

    def log_step(self, step_name: str, step_number: int, message: str = None,
                 log_level: str = "INFO", context: dict = None):
        msg = f"[JOB_ID:{self.job_id}] [{step_name}] {message or f'Executing step {step_number}'}"

        if log_level == "DEBUG":
            self.logger.debug(msg)
        elif log_level == "WARN":
            self.logger.warning(msg)
        elif log_level == "ERROR":
            self.logger.error(msg)
        else:
            self.logger.info(msg)

        add_event(f"step_{step_name}", {
            "job_id": self.job_id,
            "step_number": step_number,
            "context": json.dumps(context) if context else ""
        })

    def log_error(self, message: str, step_name: str = "EXCEPTION",
                  error_type: str = None, error_details: str = None):
        msg = f"[JOB_ID:{self.job_id}] [ERROR] {step_name}: {message}"
        self.logger.error(msg)
        add_event("error_occurred", {
            "job_id": self.job_id,
            "step_name": step_name,
            "error_type": error_type or "UNKNOWN",
            "error_details": error_details or ""
        })

    def log_end(self, status: str, rows_processed: int = 0, message: str = None):
        duration = round(time.time() - self.start_time, 3)
        self.rows_processed = rows_processed

        # Use f-string for the database name, keep parameterized (?) for the values
        query = f"""
            UPDATE {self.current_db}.UTILS.LOG_HISTORY
            SET END_TIME = CURRENT_TIMESTAMP(), 
                DURATION_SECONDS = ?,
                STATUS = ?, 
                ROWS_PROCESSED = ?,
                MESSAGE = ?
            WHERE JOB_ID = ?
        """
        params = [duration, status, rows_processed, message, self.job_id]

        try:
            self.session.sql(query, params=params).collect()
        except Exception as e:
            self.logger.warning(f"[JOB_ID:{self.job_id}] Failed to update log_end record: {e}")

        msg = f"[JOB_ID:{self.job_id}] [END] {status} | Duration: {duration}s | Rows: {rows_processed}"
        if status == "FAILED":
            self.logger.error(msg)
        else:
            self.logger.info(msg)

        add_event(f"procedure_{status.lower()}", {
            "job_id": self.job_id,
            "duration_seconds": duration,
            "rows_processed": rows_processed
        })
        
        return {"job_id": self.job_id, "status": status, "duration": duration, "rows": rows_processed}

    def send_alert(self, alert_type: str = "FAILURE"):
        try:
            # Dynamically call the correct environment's alert procedure
            if alert_type == "FAILURE":
                self.session.call(f"{self.current_db}.UTILS.SEND_FAILURE_ALERT", self.job_id)
            else:
                self.session.call(f"{self.current_db}.UTILS.SEND_SUCCESS_ALERT", self.job_id)
        except Exception as e:
            self.logger.warning(f"[JOB_ID:{self.job_id}] Failed to send {alert_type} alert: {e}")