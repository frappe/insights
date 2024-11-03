# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import ibis


def get_bigquery_connection(data_source):
    project_id = data_source.bigquery_project_id
    dataset_id = data_source.bigquery_dataset_id
    credentials = data_source.bigquery_service_account_key

    try:
        from google.oauth2 import service_account
    except ImportError:
        raise ImportError("Please install google-auth to use BigQuery as a data source")

    credentials = service_account.Credentials.from_service_account_info(
        frappe.parse_json(credentials)
    )

    return ibis.bigquery.connect(
        project_id=project_id,
        dataset_id=dataset_id,
        credentials=credentials,
    )
