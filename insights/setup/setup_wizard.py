# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _


def get_setup_stages(args=None):
    # to make setup wizard tasks run in a background job
    frappe.local.conf["trigger_site_setup_in_background"] = 1

    if frappe.db.exists("Insights Data Source", "Demo Data"):
        stages = [
            {
                "status": _("Wrapping up"),
                "fail_msg": _("Failed to login"),
                "tasks": [
                    {"fn": wrap_up, "args": args, "fail_msg": _("Failed to login")}
                ],
            }
        ]
    else:
        if args.get("setup_demo_db"):
            database_setup_stages = get_demo_setup_stages()
        else:
            database_setup_stages = [
                {
                    "status": _("Creating Data Source"),
                    "fail_msg": _("Failed to create Data Source"),
                    "tasks": [
                        {
                            "fn": create_datasource,
                            "args": args,
                            "fail_msg": _("Failed to create Data Source"),
                        }
                    ],
                }
            ]

        stages = database_setup_stages + [
            {
                "status": _("Wrapping up"),
                "fail_msg": _("Failed to login"),
                "tasks": [
                    {"fn": wrap_up, "args": args, "fail_msg": _("Failed to login")}
                ],
            },
        ]

    return stages


def get_demo_setup_stages():
    from insights.setup.demo import DemoDataFactory

    factory = DemoDataFactory()

    stages_by_fn = {
        _("Starting demo setup"): factory.initialize,
        _("Downloading data"): factory.download_demo_data,
        _("Extracting data"): factory.extract_demo_data,
        _("Inserting data"): factory.import_data,
        _("Optimizing reads"): factory.create_indexes,
        _("Creating links"): factory.create_table_links,
        _("Finishing demo setup"): factory.cleanup,
    }

    stages = []
    for stage_name, fn in stages_by_fn.items():
        stages.append(
            {
                "status": stage_name,
                "fail_msg": _("Failed to setup demo data"),
                "tasks": [
                    {
                        "fn": run_stage_task,
                        "args": frappe._dict({"task": fn}),
                        "fail_msg": _("Failed to setup demo data"),
                    }
                ],
            }
        )

    return stages


# this weird function exists
# because all stage task must have one argument (args)
def run_stage_task(args):
    return args.task()


def get_new_datasource(args):
    data_source = frappe.new_doc("Insights Data Source")
    data_source.update(
        {
            "database_type": args.get("db_type"),
            "database_name": args.get("db_name"),
            "title": args.get("db_title"),
            "host": args.get("db_host"),
            "port": args.get("db_port"),
            "username": args.get("db_username"),
            "password": args.get("db_password"),
            "use_ssl": args.get("db_use_ssl"),
        }
    )
    return data_source


def create_datasource(args):
    data_source = get_new_datasource(args)
    data_source.save()


def wrap_up(args):
    frappe.local.message_log = []
    login_as_first_user(args)

    settings = frappe.get_single("Insights Settings")
    settings.setup_complete = 1
    settings.save()


def login_as_first_user(args):
    if args.get("email") and hasattr(frappe.local, "login_manager"):
        frappe.local.login_manager.login_as(args.get("email"))


@frappe.whitelist()
def test_db_connection(db):
    db = frappe.parse_json(db)
    if db.db_type == "MariaDB":
        data_source = get_new_datasource(db)
        return data_source.test_connection()
    return False
