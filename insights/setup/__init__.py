# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import click
import frappe

from .demo import DemoDataFactory


def after_install():
    try:
        click.secho("Creating demo data...", fg="green")
        DemoDataFactory().run()
    except Exception as e:
        frappe.log_error("Failed to create Demo Data")
        click.secho(f"Error while creating demo data: {e}", fg="red")
