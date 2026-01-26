# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import time
from datetime import datetime
from typing import Any

import frappe
import pandas as pd
from frappe.core.doctype.scheduled_job_type.scheduled_job_type import parse_cron
from frappe.model.document import Document
from frappe.utils import get_datetime, now, now_datetime
from frappe.utils.password import get_decrypted_password
from frappe.utils.safe_exec import safe_exec

import insights
from insights.insights.doctype.insights_data_source_v3.ibis_utils import SafePandasDataFrame
from insights.utils import InsightsDataSourcev3


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

    def is_event_due(self, current_time=None):
        if not self.schedule:
            return False
        return self.get_next_execution() <= (current_time or now_datetime())

    def get_next_execution(self):
        """Calculate next execution time based on cron schedule and last run"""
        if not self.schedule:
            return None

        last_run = get_datetime(self.last_run or self.creation)

        next_execution = parse_cron(self.schedule).get_next(datetime, start_time=last_run)
        return next_execution

    @frappe.whitelist()
    def enqueue(self):
        enqueue_table_import_job(self.name)
        frappe.msgprint(f"Job '{self.title}' has been queued for execution.")


def enqueue_table_import_job(import_job_name: str):
    frappe.enqueue(
        "insights.insights.doctype.insights_table_import_job.insights_table_import_job.execute_table_import_job",
        import_job_name=import_job_name,
        queue="long",
        timeout=30 * 60,
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
        self.db_ctx_manager = None
        self.db = None

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
        self.db_ctx_manager = insights.warehouse.get_write_connection(schema=self.data_source.schema)
        self.db = self.db_ctx_manager.__enter__()
        self.db.raw_sql("BEGIN TRANSACTION;")
        self._log("Database transaction started")

    def _commit_transaction(self):
        if self.db:
            self._log("Committing database transaction...")
            self.db.raw_sql("COMMIT;")
            self._log("Database transaction committed successfully")

    def _rollback_transaction(self):
        if self.db:
            try:
                self._log("Rolling back database transaction due to error...")
                self.db.raw_sql("ROLLBACK;")
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
        if self.db:
            self._log("Closing database connection...")
            self.db_ctx_manager.__exit__(None, None, None)
            self.db = None
            self._log("Database connection closed")

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
            if not self._run.db:
                raise RuntimeError("No database connection available. Transaction not started.")

            exact_match_pattern = rf"^{self.name}$"
            if mode == "replace" or not self._run.db.list_tables(like=exact_match_pattern):
                self._run.db.create_table(self.name, df, overwrite=True)
            elif mode == "append":
                self._run.db.insert(self.name, df)
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
            frappe.log_error(title=f"Invalid state JSON for job {self._job.name}")
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
    """Run all scheduled import jobs that are due"""
    jobs = frappe.get_all(
        "Insights Table Import Job",
        filters={"enabled": 1, "schedule": ["is", "set"]},
        fields=["name"],
    )

    current_time = now_datetime()

    for job_data in jobs:
        try:
            job = frappe.get_doc("Insights Table Import Job", job_data.name)
            if job.is_event_due(current_time):
                enqueue_table_import_job(job.name)
        except Exception as e:
            frappe.log_error(
                title=f"Error scheduling table import job: {job_data.name}",
                message=str(e),
            )


def dump(obj):
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, indent=2, default=str)
