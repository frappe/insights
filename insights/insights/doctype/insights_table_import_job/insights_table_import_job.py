# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import time
from datetime import datetime
from functools import lru_cache
from typing import Any

import frappe
import ibis
import pandas as pd
from croniter import croniter
from frappe.model.document import Document
from frappe.utils import get_datetime, now, now_datetime
from frappe.utils.password import get_decrypted_password
from frappe.utils.safe_exec import safe_exec

from insights.insights.doctype.insights_data_source_v3.data_warehouse import WarehouseTableWriter
from insights.insights.doctype.insights_data_source_v3.ibis_utils import SafePandasDataFrame
from insights.utils import InsightsDataSourcev3

parse_cron = lru_cache(croniter)


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
                parse_cron(self.schedule)
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

    @frappe.whitelist()
    def bulk_enqueue(self, run_count: int):
        """Queue the job to run multiple times sequentially."""
        run_count = int(run_count)
        if run_count < 1 or run_count > 100:
            frappe.throw("Run count must be between 1 and 100")

        bulk_enqueue_runs(self.name, run_count)
        frappe.msgprint(f"Queued {run_count} runs for '{self.title}'")


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


def bulk_enqueue_runs(import_job_name: str, run_count: int):
    """Enqueue a chain of sequential job runs."""
    frappe.enqueue(
        "insights.insights.doctype.insights_table_import_job.insights_table_import_job.bulk_execute_runs",
        import_job_name=import_job_name,
        run_count=run_count,
        queue="long",
        timeout=run_count * 30 * 60,  # 30 min per run
        job_id=f"insights_bulk_enqueue:{import_job_name}",
    )


def bulk_execute_runs(import_job_name: str, run_count: int):
    """Execute the job N times sequentially."""
    for i in range(run_count):
        frappe.publish_realtime(
            "bulk_enqueue_progress",
            {"job": import_job_name, "current": i + 1, "total": run_count},
        )
        execute_table_import_job(import_job_name)


class TableImportJobRun:
    def __init__(self, job_name: str):
        self.job = frappe.get_doc("Insights Table Import Job", job_name)
        self.data_source = None
        self.log = None
        self.start_time = None
        self.rows_written = 0
        self.last_log_time = None
        self._table_writer: TableWriter | None = None

    def execute(self):
        try:
            self._prepare_execution()
            self._run_script()
            self._commit_table()
            self._mark_success()
        except Exception as e:
            self._rollback_table()
            self._mark_failure(e)
            raise

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

        # Create the table writer for writing data
        self._table_writer = TableWriter(self)

        self._log("Execution started")

    def _run_script(self):
        code = self.job.script

        if not code or not code.strip():
            raise ValueError("Script is empty")

        # Create a restricted table interface that only exposes insert()
        table_interface = frappe._dict(
            {
                "insert": self._table_writer.insert,
                "name": self._table_writer.name,
            }
        )

        _globals = {
            "client": self.data_source.get_api_client(),
            "table": table_interface,
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

    def _commit_table(self):
        if self._table_writer:
            self._log("Committing table writes...")
            self.rows_written = self._table_writer.commit()
            self._log(f"Table writes committed. Total rows: {self.rows_written}")

    def _rollback_table(self):
        if self._table_writer:
            try:
                self._log("Rolling back table writes due to error...")
                self._table_writer.rollback()
                self._log("Table writes rolled back successfully")
            except Exception as rollback_error:
                frappe.log_error(
                    title=f"Error rolling back table writes for job: {self.job.name}",
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

        self._log(f"Execution completed successfully. Total rows written: {self.rows_written}")

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

            traceback = frappe.as_unicode(frappe.get_traceback(with_context=True))

            self.log.db_set(
                {
                    "ended_at": now(),
                    "status": "Failed",
                    "time_taken": round(duration, 3),
                    "error": traceback,
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

    def _log(self, message: str, commit: bool = True):
        if self.last_log_time is None:
            self.last_log_time = time.monotonic()
            elapsed = 0.0
        else:
            current_time = time.monotonic()
            elapsed = current_time - self.last_log_time
            self.last_log_time = current_time

        self.log.log_output(f"[{now()}] [{elapsed:.1f}s] {message}", commit=commit)


class TableWriter:
    """Handles table writes for import jobs using WarehouseTableWriter.

    The writer is lazily initialized on first insert. Schema is inferred from
    the first DataFrame. Supports append and replace modes.
    """

    def __init__(self, run: TableImportJobRun):
        self._run = run
        self._job = run.job
        self.name = run.job.table_name
        self.database = run.data_source.schema

        # Lazy-initialized writer and schema
        self._writer: WarehouseTableWriter | None = None
        self._schema: ibis.Schema | None = None
        self._mode: str | None = None  # 'append' or 'replace'

    def insert(self, data: pd.DataFrame | list[dict], overwrite: bool = False) -> int:
        """Insert data into the table.

        Args:
            data: DataFrame or list of dicts to insert
            overwrite: If True, replaces existing data. If False, appends.

        Returns:
            Number of rows written in this batch
        """
        mode = "replace" if overwrite else "append"

        try:
            df = self._convert_to_dataframe(data)
            if df.empty:
                self._run._log(f"Warning: No data to write to table '{self.name}'")
                return 0

            row_count = len(df)

            # Handle mode changes
            if self._mode is not None and mode == "replace":
                # User called insert(overwrite=True) after previous inserts
                # Reset the writer to start fresh
                self._run._log(f"Overwrite requested. Resetting previous writes to table '{self.name}'")
                self._reset_writer()

            # Initialize writer on first insert or after reset
            if self._writer is None:
                self._init_writer(df, mode)

            self._run._log(
                f"Writing {row_count} rows to table '{self.name}' (batch {self._writer.batch_count + 1})..."
            )
            self._writer.insert(df)
            self._run._log(f"Successfully queued {row_count} rows")

            return row_count

        except Exception as e:
            error_msg = f"Error writing to table '{self.name}': {e!s}"
            self._run._log(error_msg)
            raise Exception(error_msg) from e

    def commit(self) -> int:
        if self._writer is None:
            self._run._log(f"No data to commit for table '{self.name}'")
            return 0

        try:
            total_rows = self._writer.commit()
            return total_rows
        finally:
            self._writer.__exit__(None, None, None)
            self._writer = None
            self._schema = None
            self._mode = None

    def rollback(self):
        if self._writer is not None:
            try:
                self._writer.rollback()
            finally:
                self._writer.__exit__(Exception, None, None)
                self._writer = None
                self._schema = None
                self._mode = None

    def _init_writer(self, df: pd.DataFrame, mode: str):
        """Initialize the writer with schema inferred from the first DataFrame."""
        # Infer schema from DataFrame
        self._schema = ibis.memtable(df).schema()
        self._mode = mode

        self._run._log(f"Initializing table writer for '{self.name}' in {mode} mode")
        self._writer = WarehouseTableWriter(
            self.name,
            database=self.database,
            table_schema=self._schema,
            mode=mode,
            log_fn=self._run._log,
        )
        self._writer.__enter__()

    def _reset_writer(self):
        """Reset the writer, discarding any pending writes."""
        if self._writer is not None:
            self._writer.rollback()
            self._writer = None
            self._schema = None
            self._mode = None

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
