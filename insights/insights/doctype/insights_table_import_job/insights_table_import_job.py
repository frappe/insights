# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import time
from typing import Any

import frappe
import pandas as pd
from croniter import croniter
from frappe.model.document import Document
from frappe.utils import get_datetime, now, now_datetime
from frappe.utils.password import get_decrypted_password
from frappe.utils.safe_exec import safe_exec

import insights
from insights.insights.doctype.insights_data_source_v3.ibis_utils import SafePandasDataFrame
from insights.utils import InsightsDataSourcev3

MAX_EXECUTION_TIME = 900


class InsightsTableImportJob(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from insights.insights.doctype.insights_secret_key.insights_secret_key import InsightsSecretKey

        data_source: DF.Link
        enabled: DF.Check
        last_log: DF.Link | None
        last_run: DF.Datetime | None
        last_status: DF.Data | None
        schedule: DF.Data | None
        script: DF.Code
        secrets: DF.Table[InsightsSecretKey]
        state: DF.Code | None
        table_name: DF.Data
        title: DF.Data
    # end: auto-generated types

    def validate(self):
        """Validate the job document."""
        self.validate_cron_expression()

    def validate_cron_expression(self):
        """Validate that the cron expression is valid if provided."""
        if self.schedule:
            try:
                from croniter import croniter

                croniter(self.schedule)
            except Exception as e:
                frappe.throw(f"Invalid cron expression: {e!s}")

    def on_update(self):
        self.table_name = frappe.scrub(self.table_name)

    @frappe.whitelist()
    def enqueue(self):
        enqueue_table_import_job(self.name)
        frappe.msgprint(f"Job '{self.title}' has been queued for execution.")


def enqueue_table_import_job(import_job_name: str):
    frappe.enqueue(
        "insights.insights.doctype.insights_table_import_job.insights_table_import_job.execute_table_import_job",
        import_job_name=import_job_name,
        queue="long",
        timeout=MAX_EXECUTION_TIME + 60,
        job_id=f"insights_table_import_job:{import_job_name}",
    )


def execute_table_import_job(import_job_name: str):
    run = TableImportJobRun(import_job_name)
    run.execute()


class TableImportJobRun:
    def __init__(self, job_name: str):
        self.job = frappe.get_doc("Insights Table Import Job", job_name)
        self.data_source = None
        self.log = None
        self.start_time = None
        self.rows_written = 0
        self.db_connection = None

    def execute(self):
        try:
            self._prepare_execution()
            self._start_transaction()
            self._run_script()
            self._commit_transaction()
            self._mark_success()
        except Exception as e:
            self._rollback_transaction()
            self._mark_failure(e)
            raise
        finally:
            self._cleanup()

    def _prepare_execution(self):
        self.start_time = time.monotonic()
        self.data_source = InsightsDataSourcev3.get_doc(self.job.data_source)

        # Create log immediately so users can see execution status even if job fails early
        self.log = frappe.get_doc(
            {
                "doctype": "Insights Table Import Log",
                "data_source": self.data_source.name,
                "table_name": self.job.table_name,
                "import_job": self.job.name,
                "query": self.job.script,
                "status": "In Progress",
                "started_at": now(),
            }
        )
        self.log.insert(ignore_permissions=True)
        frappe.db.commit()

        self._log("Execution started")

    def _run_script(self):
        code = self.job.script

        if not code or not code.strip():
            raise ValueError("Script is empty")

        _globals = {
            "client": self.data_source.get_api_client(),
            "table": JobTable(self),
            "state": JobState(self.job),
            "secrets": JobSecrets(self.job),
            "log": self._log,
            "pandas": frappe._dict(
                {
                    "DataFrame": SafePandasDataFrame,
                }
            ),
        }

        _locals = {}

        self._log("Executing script...")

        safe_exec(
            code,
            _globals=_globals,
            _locals=_locals,
            restrict_commit_rollback=True,
        )

        self._log("Script executed successfully")

    def _start_transaction(self):
        self._log("Starting database transaction...")
        self.db_connection = insights.warehouse.get_write_connection()
        self.db_connection.__enter__()
        self.db_connection.raw_sql("BEGIN TRANSACTION;")
        self._log("Database transaction started")

    def _commit_transaction(self):
        if self.db_connection:
            self._log("Committing database transaction...")
            self.db_connection.raw_sql("COMMIT;")
            self._log("Database transaction committed successfully")

    def _rollback_transaction(self):
        if self.db_connection:
            try:
                self._log("Rolling back database transaction due to error...")
                self.db_connection.raw_sql("ROLLBACK;")
                self._log("Database transaction rolled back successfully")
            except Exception as rollback_error:
                frappe.log_error(
                    title=f"Error rolling back transaction for job: {self.job.name}",
                    message=str(rollback_error),
                )

    def _mark_success(self):
        duration = time.monotonic() - self.start_time

        self.log.db_set(
            {
                "ended_at": now(),
                "status": "Completed",
                "time_taken": round(duration, 3),
                "rows_imported": self.rows_written,
            },
            commit=True,
        )

        self._log(f"Execution completed. Total rows written: {self.rows_written}")

        self.job.db_set(
            {
                "last_run": now(),
                "last_status": "Success",
                "last_log": self.log.name,
            },
            commit=True,
        )

    def _mark_failure(self, error: Exception):
        try:
            duration = time.monotonic() - self.start_time

            self.log.db_set(
                {
                    "ended_at": now(),
                    "status": "Failed",
                    "time_taken": round(duration, 3),
                    "error": str(error),
                },
                commit=True,
            )

            self._log(f"Execution failed: {error!s}")

            self.job.db_set(
                {
                    "last_run": now(),
                    "last_status": "Failed",
                    "last_log": self.log.name,
                },
                commit=True,
            )

        except Exception as e:
            frappe.log_error(
                title=f"Error marking job run as failed: {self.job.name}",
                message=str(e),
            )

    def _cleanup(self):
        if self.db_connection:
            try:
                self.db_connection.__exit__(None, None, None)
                self.db_connection = None
            except Exception as e:
                frappe.log_error(
                    title=f"Error closing database connection for job: {self.job.name}",
                    message=str(e),
                )

    def _log(self, message: str, commit: bool = True):
        self.log.log_output(f"[{now()}] {message}", commit=commit)


class JobTable:
    def __init__(self, run: TableImportJobRun):
        self._run = run
        self._job = run.job

        self.name = run.job.table_name

    def insert(self, data: pd.DataFrame | list[dict], overwrite: bool = False):
        return self._write(data, "replace" if overwrite else "append")

    def upsert(self, data: pd.DataFrame | list[dict]):
        raise NotImplementedError("Upsert mode is not yet supported")

    def _write(self, data: Any, mode: str) -> int:
        try:
            if mode not in ["append", "replace"]:
                raise ValueError("Mode must be 'append' or 'replace'")

            df = self._convert_to_dataframe(data)
            if df.empty:
                self._run._log(f"Warning: No data to write to table '{self.name}'")
                return 0

            row_count = len(df)
            self._run._log(f"Writing {row_count} rows to table '{self.name}' in {mode} mode...")

            # Use the shared connection from the run (transactional)
            db = self._run.db_connection
            if not db:
                raise RuntimeError("No database connection available. Transaction not started.")

            exact_match_pattern = rf"^{self.name}$"
            if mode == "replace" or not db.list_tables(like=exact_match_pattern):
                db.create_table(self.name, df, overwrite=True)
            elif mode == "append":
                db.insert(self.name, df)
            else:
                raise ValueError(f"Unsupported mode: {mode}")

            self._run._log(f"Successfully wrote {row_count} rows to table '{self.name}'")
            self._run.rows_written += row_count
            return row_count

        except Exception as e:
            error_msg = f"Error writing to table '{self.name}': {e!s}"
            self._run._log(error_msg)
            raise Exception(error_msg) from e

    def _convert_to_dataframe(self, data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        else:
            raise ValueError("Data must be a pandas DataFrame or list of dicts")


class JobState:
    def __init__(self, job: InsightsTableImportJob):
        self._job = job
        self._state = self._load_state()

    def _load_state(self) -> dict:
        state_json = self._job.state or "{}"
        try:
            return json.loads(state_json)
        except json.JSONDecodeError:
            frappe.logger().warning(f"Invalid state JSON for job {self._job.name}, resetting to empty dict")
            return {}

    def _save_state(self):
        self._job.db_set("state", dump(self._state), commit=True)

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def set(self, key: str, value):
        self._state[key] = value
        self._save_state()

    def delete(self, key: str):
        if key in self._state:
            del self._state[key]
            self._save_state()

    def clear(self):
        self._state = {}
        self._save_state()


class JobSecrets:
    def __init__(self, job: InsightsTableImportJob):
        self._job = job
        self._secrets_cache = {}

    def get(self, key: str) -> str | None:
        # Cache to avoid repeated decryption overhead
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        for secret in self._job.secrets:
            if secret.key == key:
                value = get_decrypted_password(
                    "Insights Secret Key",
                    secret.name,
                    "value",
                )
                self._secrets_cache[key] = value
                return value

        return None


def run_scheduled_imports():
    jobs = frappe.get_all(
        "Insights Table Import Job",
        filters={"enabled": 1},
        fields=["name", "schedule", "last_run"],
    )

    current_time = now_datetime()

    for job in jobs:
        if not job.schedule:
            continue

        try:
            if is_job_due(job.schedule, job.last_run, current_time):
                frappe.logger().info(f"Enqueueing table import job: {job.name}")
                enqueue_table_import_job(job.name)
        except Exception as e:
            frappe.log_error(
                title=f"Error scheduling table import job: {job.name}",
                message=str(e),
            )


def is_job_due(cron_expression: str, last_run: str | None, current_time) -> bool:
    """
    Check if a job is due to run based on its cron schedule.

    Args:
            cron_expression: Cron expression (e.g., "0 */6 * * *")
            last_run: Last run datetime string
            current_time: Current datetime

    Returns:
            True if job should run now
    """
    try:
        croniter(cron_expression)
    except Exception:
        frappe.logger().warning(f"Invalid cron expression: {cron_expression}")
        return False

    # If never run, check if we're past the most recent scheduled time
    if not last_run:
        cron = croniter(cron_expression, current_time)
        # Get the most recent scheduled time before now
        prev_scheduled_dt = cron.get_prev(return_datetime=True)
        # Run if the most recent schedule was within the last hour (scheduler interval)
        # This prevents running on every check
        time_since_scheduled = (current_time - prev_scheduled_dt).total_seconds()
        return 0 <= time_since_scheduled <= 3600  # Within last hour

    # Get last run datetime
    last_run_dt = get_datetime(last_run)

    # Handle edge case: last_run is in the future (clock skew)
    if last_run_dt > current_time:
        frappe.logger().warning(f"Last run time {last_run_dt} is in the future. Skipping execution.")
        return False

    # Get next scheduled time after last run
    cron = croniter(cron_expression, last_run_dt)
    next_scheduled_dt = cron.get_next(return_datetime=True)

    # If next scheduled time has passed, it's due
    return next_scheduled_dt <= current_time


def dump(obj):
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, indent=2, default=str)
